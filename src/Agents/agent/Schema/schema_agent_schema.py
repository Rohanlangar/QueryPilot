# agent/Schema/schema_agent_schema.py
from pydantic import BaseModel, Field
from typing import List


class SchemaSelectionOutput(BaseModel):
    """Structured output for the Schema Agent.

    The agent selects which tables from a candidate list are relevant
    to answering the user's natural-language question.
    """

    relevant_tables: List[str] = Field(
        description="Exact table names (from the candidate list) relevant to the question."
    )
    reasoning: str = Field(
        description="One short sentence explaining the selection."
    )
