"""Query Planning Agent — LangGraph Node.

Determines whether a user's question requires a single database or multiple
independent databases (federated query). Produces a structured query plan
specifying required databases, tables, sub-queries, and application-level join keys.
"""

import logging
from typing import Dict, Any, List
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from agent.Prompts.query_planner_prompt import (
    QUERY_PLANNER_SYSTEM_PROMPT,
    build_query_planner_user_prompt,
)
from agent.Schema.query_planner_schema import QueryPlanOutput, JoinKeyMapping
from config import SCHEMA_AGENT_MODEL, OLLAMA_BASE_URL

logger = logging.getLogger("querypilot.federation")


def _heuristic_query_plan(
    question: str,
    unified_schema: Dict[str, Any],
    cross_db_relationships: List[Dict[str, Any]],
    conversation_history: List[Dict[str, Any]] = None,
) -> QueryPlanOutput:
    q_lower = (question or "").lower()
    matched_dbs = {}

    # Check multi-turn conversation history for refinements (e.g. "only show...", "below 20")
    if conversation_history:
        if any(q_lower.startswith(w) for w in ("only", "filter", "where", "show only", "limit to", "just ", "below ")):
            for prev in reversed(conversation_history):
                prev_q = prev.get("content", "")
                if prev_q:
                    prev_plan = _heuristic_query_plan(prev_q, unified_schema, cross_db_relationships)
                    if prev_plan.required_databases:
                        return prev_plan

    # Precise table and column matching per database
    for db_id, db_data in unified_schema.items():
        tables = db_data.get("tables", {})
        matched_tables = []
        for t_name, t_meta in tables.items():
            t_lower = t_name.lower()
            # If exact table or singular/plural name matches
            if t_lower in q_lower or (len(t_lower) > 3 and t_lower.rstrip("s") in q_lower):
                matched_tables.append(t_name)
        if matched_tables:
            matched_dbs[db_id] = matched_tables

    # Semantic domain mapping
    if ("demand" in q_lower or "sales" in q_lower or "order" in q_lower) and "order_metrics" not in q_lower:
        for db_id, db_data in unified_schema.items():
            if "order" in db_id.lower() or "sales" in db_id.lower():
                for t in db_data.get("tables", {}).keys():
                    if t.lower() == "orders" or "order" in t.lower():
                        matched_dbs.setdefault(db_id, []).append(t)
                        break

    if "inventory" in q_lower or "stock" in q_lower or ("product" in q_lower and "inventory" in str(unified_schema).lower()):
        for db_id, db_data in unified_schema.items():
            if "inventory" in db_id.lower() or "stock" in db_id.lower():
                for t in db_data.get("tables", {}).keys():
                    if "inventory" in t.lower() or "stock" in t.lower():
                        matched_dbs.setdefault(db_id, []).append(t)
                        break

    if "payment" in q_lower or "paid" in q_lower or "transaction" in q_lower:
        for db_id, db_data in unified_schema.items():
            if "payment" in db_id.lower():
                for t in db_data.get("tables", {}).keys():
                    if "payment" in t.lower():
                        matched_dbs.setdefault(db_id, []).append(t)
                        break

    if "metric" in q_lower or "analytics" in q_lower:
        for db_id, db_data in unified_schema.items():
            if "analytics" in db_id.lower() or "metric" in db_id.lower():
                matched_dbs.setdefault(db_id, []).extend(list(db_data.get("tables", {}).keys()))

    # Deduplicate tables per DB
    matched_dbs = {db: sorted(list(set(tbls))) for db, tbls in matched_dbs.items() if tbls}

    # If nothing matched, pick first available database and its first table
    if not matched_dbs:
        first_db = next(iter(unified_schema.keys())) if unified_schema else "default"
        first_tables = list(unified_schema.get(first_db, {}).get("tables", {}).keys()) if unified_schema else ["orders"]
        matched_dbs = {first_db: first_tables[:1]}

    is_fed = len(matched_dbs) > 1
    join_keys = []
    if is_fed:
        # Find connecting relationship between matched databases
        db_list = list(matched_dbs.keys())
        for rel in cross_db_relationships:
            s_db = rel.get("source_db")
            t_db = rel.get("target_db")
            jk_col = rel.get("join_key", "")
            if s_db in db_list and t_db in db_list:
                # Prioritize join keys mentioned in question or core entity IDs
                priority = (jk_col in q_lower) or jk_col in ("product_id", "order_id", "customer_id", "user_id")
                if priority or not join_keys:
                    join_keys.append(
                        JoinKeyMapping(
                            db1=s_db,
                            col1=rel.get("source_column"),
                            db2=t_db,
                            col2=rel.get("target_column"),
                        )
                    )

    # Sort join keys to prioritize entity IDs mentioned in question
    join_keys.sort(key=lambda jk: (jk.col1 in q_lower or jk.col1 == "product_id"), reverse=True)
    if join_keys:
        join_keys = join_keys[:1]  # Keep primary join key between the two DBs

    sub_goals = {}
    for db_id, tbls in matched_dbs.items():
        sub_goals[db_id] = f"Retrieve relevant records from {', '.join(tbls)} for '{question[:40]}'"

    return QueryPlanOutput(
        is_federated=is_fed,
        required_databases=list(matched_dbs.keys()),
        required_tables=matched_dbs,
        sub_goals=sub_goals,
        join_keys=join_keys,
        join_type="inner",
        post_join_operations={},
        reasoning=f"Heuristic plan selected databases: {list(matched_dbs.keys())}",
    )


def query_planner_node(state: dict) -> dict:
    """LangGraph node: analyze question across unified schemas and produce QueryPlan.

    Reads:
        state["question"]
        state["unified_schema"]
        state["cross_db_relationships"]
        state.get("conversation_history")

    Returns partial state update:
        {
            "query_plan": dict,
            "is_federated": bool,
            "relevant_schema": dict,
        }
    """
    question = state.get("question", "")
    unified_schema = state.get("unified_schema", {})
    cross_db_rels = state.get("cross_db_relationships", [])
    history = state.get("conversation_history", [])

    logger.info(f"[FEDERATION] Analyzing Question: \"{question}\"")
    logger.info(f"[FEDERATION] Available Active Databases: {list(unified_schema.keys())}")

    plan: QueryPlanOutput = None

    try:
        llm = ChatOllama(
            model=SCHEMA_AGENT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
        )
        structured_llm = llm.with_structured_output(
            QueryPlanOutput, method="json_schema"
        )
        messages = [
            SystemMessage(content=QUERY_PLANNER_SYSTEM_PROMPT),
            HumanMessage(
                content=build_query_planner_user_prompt(
                    question=question,
                    unified_schema=unified_schema,
                    cross_db_relationships=cross_db_rels,
                    conversation_history=history,
                )
            ),
        ]
        plan = structured_llm.invoke(messages)
    except Exception as e:
        logger.warning(f"Query planner LLM call failed or unavailable ({e}); utilizing deterministic heuristic planner.")

    if not plan or not plan.required_databases:
        plan = _heuristic_query_plan(
            question=question,
            unified_schema=unified_schema,
            cross_db_relationships=cross_db_rels,
            conversation_history=history,
        )

    # Sanitize required_databases against unified_schema
    valid_dbs = [db for db in plan.required_databases if db in unified_schema]
    if not valid_dbs:
        valid_dbs = list(unified_schema.keys())[:1]
    is_fed = len(valid_dbs) > 1

    plan_dict = {
        "is_federated": is_fed,
        "required_databases": valid_dbs,
        "required_tables": {db: plan.required_tables.get(db, []) for db in valid_dbs},
        "sub_goals": {db: plan.sub_goals.get(db, "") for db in valid_dbs},
        "join_keys": [jk.model_dump() if hasattr(jk, "model_dump") else dict(jk) for jk in plan.join_keys],
        "join_type": plan.join_type,
        "post_join_operations": plan.post_join_operations or {},
        "reasoning": plan.reasoning,
    }

    # Build flattened relevant_schema for downstream backward compatibility
    flattened_schema = {}
    for db_id in valid_dbs:
        db_tables = unified_schema.get(db_id, {}).get("tables", {})
        tbl_names = plan_dict["required_tables"].get(db_id) or list(db_tables.keys())
        for t in tbl_names:
            if t in db_tables:
                # Add table prefixed with db_id if collision, else table name
                key = t if t not in flattened_schema else f"{db_id}.{t}"
                flattened_schema[key] = db_tables[t]

    logger.info(f"[FEDERATION] Databases Selected: {valid_dbs} (is_federated={is_fed})")
    logger.info(f"[FEDERATION] Tables Selected: {plan_dict['required_tables']}")
    if is_fed:
        logger.info(f"[FEDERATION] Join Keys: {plan_dict['join_keys']}")

    return {
        "query_plan": plan_dict,
        "is_federated": is_fed,
        "relevant_schema": flattened_schema,
    }
