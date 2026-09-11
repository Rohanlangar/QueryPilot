"""Prompt templates for the Federated Query Planning Agent."""

import json
from typing import Dict, Any, List

QUERY_PLANNER_SYSTEM_PROMPT = """You are an expert Federated SQL Query Planner for an organization with an enterprise microservices architecture.
Multiple independent databases are connected (e.g. order_db, inventory_db, payment_db, analytics_db).
Your goal is to inspect the user's natural language question and the available database schemas, then decide:
1. Does answering this question require ONE database (simple query), or MULTIPLE databases (federated query)?
2. Which databases and tables are required?
3. For each required database, what is the specific query objective / sub-goal?
4. If multiple databases are required, what are the join keys (e.g. product_id, order_id, customer_id)?
   Remember: Independent databases cannot be directly joined in PostgreSQL via SQL.
   The backend application will execute independent queries on each database and perform the join/merge in-memory.
5. In multi-turn conversations, preserve context from previous questions and queries. Reuse previous databases and join keys when refining previous answers.

Return your response adhering to the requested JSON schema.
"""


def build_query_planner_user_prompt(
    question: str,
    unified_schema: Dict[str, Any],
    cross_db_relationships: List[Dict[str, Any]],
    conversation_history: List[Dict[str, Any]] = None,
) -> str:
    """Construct the user prompt for the Query Planning Agent."""
    # Format available databases and tables
    db_summaries = []
    for db_id, db_data in unified_schema.items():
        db_name = db_data.get("database_name", db_id)
        dialect = db_data.get("dialect", "unknown")
        tables_meta = db_data.get("tables", {})
        tbl_lines = []
        for t_name, t_meta in tables_meta.items():
            cols = t_meta.get("columns", {})
            cols_str = ", ".join(f"{c} ({t})" for c, t in cols.items())
            pks = t_meta.get("primary_keys", [])
            fks = t_meta.get("foreign_keys", [])
            pk_str = f" [PK: {', '.join(pks)}]" if pks else ""
            fk_str = f" [FKs: {len(fks)}]" if fks else ""
            tbl_lines.append(f"    - Table '{t_name}'{pk_str}{fk_str}: {cols_str}")
        db_summaries.append(
            f"Database '{db_id}' (Name: {db_name}, Dialect: {dialect}):\n" + "\n".join(tbl_lines)
        )

    schemas_text = "\n\n".join(db_summaries)

    # Format cross-database relationships
    rel_lines = []
    for rel in cross_db_relationships[:15]:
        rel_lines.append(f"  - {rel.get('description')} (Join Key: {rel.get('join_key')})")
    rels_text = "\n".join(rel_lines) if rel_lines else "  None auto-detected."

    # Format conversation history
    hist_text = "None"
    if conversation_history:
        turns = []
        for h in conversation_history[-3:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            sql = h.get("sql", "")
            turns.append(f"  {role.upper()}: {content}" + (f"\n    (Prior SQL: {sql})" if sql else ""))
        hist_text = "\n".join(turns)

    return f"""USER QUESTION:
"{question}"

CONVERSATION HISTORY (Last turns):
{hist_text}

AVAILABLE CONNECTED DATABASES & SCHEMAS:
{schemas_text}

DETECTED CROSS-DATABASE RELATIONSHIP CANDIDATES:
{rels_text}

Determine the query execution strategy:
1. Is it single database or federated across multiple databases?
2. Which databases and tables are needed?
3. What is the sub-goal for each database?
4. What are the join keys and join type?
5. How should results be filtered or aggregated?
"""
