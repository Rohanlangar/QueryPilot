from pydantic import BaseModel, Field
from typing import List, Literal


class ExplanationOutput(BaseModel):
    """Structured output for the Explanation Agent.

    Provides an explanation of the SQL query logic and execution, confidence rating,
    and suggested follow-up questions.
    """

    explanation: str = Field(
        description="Clear technical and logical explanation of the SQL query, detailing the tables queried, columns selected, joins/filters/sorting/limit applied, and how it retrieves the requested data."
    )
    confidence_label: Literal["High", "Medium", "Low"] = Field(
        description="Confidence rating: High, Medium, or Low."
    )
    confidence_reason: str = Field(
        description="Brief justification for the confidence rating based on schema mapping and query logic."
    )
    suggested_followups: List[str] = Field(
        description="2 relevant follow-up questions or queries the user might want to run next."
    )
