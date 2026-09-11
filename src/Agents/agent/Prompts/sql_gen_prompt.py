# agent/Prompts/sql_gen_prompt.py
"""Prompt templates for the SQL Generation Agent.

This file contains ONLY prompt strings and prompt-builder functions.
No LLM calls, no logic.
"""

SQL_GEN_SYSTEM_PROMPT = """You are an expert {dialect} SQL generator.

Rules:
- Use ONLY the tables and columns provided in the schema. Never invent columns.
- Pay close attention to Foreign Key relationships when joining tables.
- If a column provides valid sample values, use the EXACT matching casing and value in WHERE clauses.
- Use CTEs for multi-step logic instead of nested subqueries.
- Never use SELECT * — always list explicit columns.
- Add a LIMIT of {row_limit} unless the user explicitly asks for all rows.
- If validation or database execution errors from a previous attempt are provided, fix exactly those issues
  without changing the query's original intent."""


def build_sql_gen_user_prompt(
    question: str, schema: dict, prior_sql: str = "", errors: list = None
) -> str:
    """Build the user-facing prompt, optionally including retry context."""
    error_block = ""
    if errors:
        error_block = (
            f"\n\nPrevious attempt failed validation:\n"
            + "\n".join(errors)
            + f"\nPrevious SQL:\n{prior_sql}"
        )
    return f"Question: {question}\n\nSchema:\n{schema}{error_block}"
