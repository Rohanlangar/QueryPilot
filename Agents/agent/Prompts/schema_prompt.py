# agent/Prompts/schema_prompt.py
"""Prompt templates for the Schema Selection Agent.

This file contains ONLY prompt strings and prompt-builder functions.
No LLM calls, no logic.
"""

SCHEMA_SYSTEM_PROMPT = """You are a database schema analyst.
You are given a user's natural-language question and a shortlist of candidate tables
(already narrowed down by embedding similarity — this is NOT the full database schema).

Select ONLY the tables and columns from the candidates that are actually needed to
answer the question. Prefer fewer, more precise tables over broad selection. Do not
invent table or column names that are not in the candidate list."""


def build_schema_user_prompt(question: str, candidate_schema: dict) -> str:
    """Build the user-facing prompt with the question and candidate tables."""
    return f"Question: {question}\n\nCandidate tables:\n{candidate_schema}"
