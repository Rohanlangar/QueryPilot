# agent/Schema/explanation_schema.py
from pydantic import BaseModel
from typing import List, Literal


class ExplanationOutput(BaseModel):
    """Structured output for the Explanation Agent.

    Provides a plain-English explanation, confidence rating, and
    suggested follow-up questions for the business user.
    """

    explanation: str
    confidence_label: Literal["High", "Medium", "Low"]
    confidence_reason: str
    suggested_followups: List[str]
