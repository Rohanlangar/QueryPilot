# agent/sql_gen_agent.py
"""SQL Generation Agent — Graph Node.

Generates database-specific SQL query/queries from the natural-language
question and the relevant schema.
Supports both:
  1. Single-database queries
  2. Multi-database federated queries (generates separate SQL for each target DB)
Supports validation retry loops for self-healing error recovery.
"""

import logging
from typing import Dict, Any, List
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from agent.Prompts.sql_gen_prompt import SQL_GEN_SYSTEM_PROMPT, build_sql_gen_user_prompt
from agent.Schema.sql_gen_schema import SQLGenerationOutput
from config import SQL_GEN_MODEL, DEFAULT_ROW_LIMIT, OLLAMA_BASE_URL

logger = logging.getLogger("querypilot.federation")


def _generate_single_sql(
    question: str,
    schema: dict,
    dialect: str = "sqlite",
    prior_sql: str = "",
    prior_errors: list = None,
    required_columns: list = None,
) -> str:
    """Generate a single SQL query for a given database schema and objective."""
    augmented_question = question
    if required_columns:
        augmented_question += f" (Ensure columns [{', '.join(required_columns)}] are included in SELECT for cross-database join)."

    try:
        llm = ChatOllama(
            model=SQL_GEN_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
        )
        structured_llm = llm.with_structured_output(
            SQLGenerationOutput, method="json_schema"
        )
        messages = [
            SystemMessage(
                content=SQL_GEN_SYSTEM_PROMPT.format(
                    dialect=dialect,
                    row_limit=DEFAULT_ROW_LIMIT,
                )
            ),
            HumanMessage(
                content=build_sql_gen_user_prompt(
                    augmented_question,
                    schema,
                    prior_sql,
                    prior_errors if prior_errors else None,
                )
            ),
        ]
        result: SQLGenerationOutput = structured_llm.invoke(messages)
        sql = result.sql.strip().rstrip(";")
        return sql
    except Exception as e:
        logger.warning(f"SQL generation LLM failed ({e}); building fallback SQL.")
        return _build_fallback_sql(question, schema, required_columns)


def _build_fallback_sql(question: str, schema: dict, required_columns: list = None) -> str:
    """Deterministic SQL generator for fallback situations."""
    if not schema:
        return "SELECT 1"
    first_tbl = next(iter(schema.keys()))
    tbl_cols = list(schema[first_tbl].get("columns", {}).keys())
    select_cols = []
    if required_columns:
        for rc in required_columns:
            if rc in tbl_cols:
                select_cols.append(rc)
    for c in tbl_cols:
        if c not in select_cols and len(select_cols) < 5:
            select_cols.append(c)

    q_lower = question.lower()
    cols_str = ", ".join(select_cols) if select_cols else "*"

    # For orders table or tables with quantity/amount where demand is asked
    if ("demand" in q_lower or "quantity" in q_lower or "sum" in q_lower) and "inventory" not in first_tbl.lower():
        qty_col = next((c for c in tbl_cols if any(k in c.lower() for k in ("quant", "amount", "qty"))), None)
        id_col = None
        if required_columns:
            id_col = next((rc for rc in required_columns if rc in tbl_cols), None)
        if not id_col:
            id_col = next((c for c in tbl_cols if c.endswith("_id")), None)
        if qty_col and id_col:
            return f"SELECT {id_col}, SUM({qty_col}) AS demand FROM {first_tbl} GROUP BY {id_col} LIMIT {DEFAULT_ROW_LIMIT}"

    return f"SELECT {cols_str} FROM {first_tbl} LIMIT {DEFAULT_ROW_LIMIT}"


def sql_gen_node(state: dict) -> dict:
    """LangGraph node: generate SQL for single or multiple target databases.

    Reads:
        state["question"]
        state.get("is_federated", False)
        state.get("query_plan", {})
        state.get("unified_schema", {})
        state.get("relevant_schema", {})
        state.get("db_dialect", "sqlite")
        state.get("validation_errors", [])
        state.get("execution_error")

    Returns partial state update:
        {
            "database_queries": {db_id: sql},
            "generated_sql": str,
            "sql_gen_attempts": int,
            "validation_errors": [],
            "execution_error": None,
        }
    """
    is_federated = state.get("is_federated", False)
    query_plan = state.get("query_plan", {})
    unified_schema = state.get("unified_schema", {})
    relevant_schema = state.get("relevant_schema", {})
    default_dialect = state.get("db_dialect", "sqlite")

    prior_errors = list(state.get("validation_errors") or [])
    if state.get("execution_error"):
        prior_errors.append(f"Database runtime error: {state['execution_error']}")

    database_queries: Dict[str, str] = {}

    if not is_federated or len(query_plan.get("required_databases", [])) <= 1:
        # ── Single Database Query ─────────────────────────────────────────
        target_db = (
            query_plan.get("required_databases", [None])[0]
            or state.get("connection_id")
            or (next(iter(unified_schema.keys())) if unified_schema else "default")
        )
        db_meta = unified_schema.get(target_db, {})
        db_schema = db_meta.get("tables", {}) or relevant_schema
        dialect = db_meta.get("dialect", default_dialect)
        prior_sql = state.get("optimized_sql") or state.get("generated_sql", "")

        sql = _generate_single_sql(
            question=state["question"],
            schema=db_schema,
            dialect=dialect,
            prior_sql=prior_sql,
            prior_errors=prior_errors,
        )
        database_queries[target_db] = sql
        combined_sql = sql

    else:
        # ── Multi-Database Federated Queries ──────────────────────────────
        required_dbs = query_plan.get("required_databases", [])
        sub_goals = query_plan.get("sub_goals", {})
        join_keys = query_plan.get("join_keys", [])

        # Map required join columns per database
        db_join_cols: Dict[str, List[str]] = {db: [] for db in required_dbs}
        for jk in join_keys:
            db1 = jk.get("db1")
            col1 = jk.get("col1")
            db2 = jk.get("db2")
            col2 = jk.get("col2")
            if db1 in db_join_cols and col1:
                db_join_cols[db1].append(col1)
            if db2 in db_join_cols and col2:
                db_join_cols[db2].append(col2)

        sql_blocks = []
        for db_id in required_dbs:
            db_meta = unified_schema.get(db_id, {})
            db_schema = db_meta.get("tables", {})
            req_tables = query_plan.get("required_tables", {}).get(db_id, [])
            if req_tables:
                filtered_schema = {t: db_schema[t] for t in req_tables if t in db_schema}
            else:
                filtered_schema = db_schema

            dialect = db_meta.get("dialect", default_dialect)
            sub_goal = sub_goals.get(db_id) or f"Query for {state['question']} from database {db_id}"
            req_cols = db_join_cols.get(db_id, [])

            db_sql = _generate_single_sql(
                question=sub_goal,
                schema=filtered_schema or db_schema,
                dialect=dialect,
                required_columns=req_cols,
            )
            database_queries[db_id] = db_sql
            sql_blocks.append(f"-- [{db_id}]\n{db_sql};")

        combined_sql = "\n\n".join(sql_blocks)

    logger.info(f"[SQL GEN] Generated queries for {len(database_queries)} database(s):")
    for db_id, q in database_queries.items():
        logger.info(f"  - {db_id}: {q}")

    return {
        "database_queries": database_queries,
        "generated_sql": combined_sql,
        "sql_gen_attempts": state.get("sql_gen_attempts", 0) + 1,
        "validation_errors": [],
        "execution_error": None,
    }
