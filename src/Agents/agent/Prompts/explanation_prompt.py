# agent/Prompts/explanation_prompt.py
"""Prompt templates for the Explanation Agent.

This file contains ONLY prompt strings and prompt-builder functions.
No LLM calls, no logic.
"""

EXPLANATION_SYSTEM_PROMPT = """You are explaining query results to a non-technical
business user.

1. State the direct answer to the question in plain English (1-2 sentences).
2. Point out one notable pattern or outlier if present.
3. Rate confidence: "High" if the query directly and unambiguously answers the question,
   "Medium" if you made an assumption about column meaning, "Low" if the result seems
   incomplete or the question was ambiguous.
4. Suggest 2 relevant follow-up questions."""


def build_explanation_user_prompt(
    question: str, sql: str, row_count: int, sample_rows: list
) -> str:
    """Build the user-facing prompt with the question, SQL, and result sample."""
    return (
        f"Question: {question}\n"
        f"SQL run: {sql}\n"
        f"Result ({row_count} rows, showing sample):\n{sample_rows}"
    )
