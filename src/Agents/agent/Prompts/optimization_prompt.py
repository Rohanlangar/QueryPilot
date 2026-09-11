# agent/Prompts/optimization_prompt.py
"""Prompt templates for the Optimization Agent.

This file contains ONLY prompt strings and prompt-builder functions.
No LLM calls, no logic.
"""

OPTIMIZATION_SYSTEM_PROMPT = """You are a SQL performance reviewer for {dialect}.
Given a validated query and table row counts, suggest safe improvements:
- Rewrite correlated subqueries as JOINs where equivalent.
- Suggest an index if a WHERE/JOIN column is unindexed and the table has >100k rows.
- Flag if the query could return an unbounded result set.
If no changes are needed, return the original SQL unchanged."""


def build_optimization_user_prompt(sql: str, row_counts: dict) -> str:
    """Build the user-facing prompt with the SQL and table row counts."""
    return f"Query:\n{sql}\n\nTable row counts:\n{row_counts}"
