# agent/Schema/ambiguity_schema.py
"""Pydantic schema for Ambiguity Detection Agent."""

from pydantic import BaseModel, Field
from typing import Optional


class AmbiguityCheckOutput(BaseModel):
    """Structured output for the Ambiguity Detection Agent.

    Determines if the user's natural language request is underspecified,
    open to multiple conflicting interpretations, or missing essential criteria
    where guessing would produce dangerous or incorrect SQL.
    """

    is_ambiguous: bool = Field(
        description="True if the question is ambiguous or lacks required context; False if clear and answerable directly."
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Concise, friendly clarification question to ask the user if is_ambiguous is True. Must be None if is_ambiguous is False."
    )
    reasoning: str = Field(
        description="Short 1-sentence reasoning for the decision."
    )
