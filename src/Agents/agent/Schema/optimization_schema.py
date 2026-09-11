# agent/Schema/optimization_schema.py
from pydantic import BaseModel, Field
from typing import List, Literal


class OptimizationOutput(BaseModel):
    """Structured output for the Optimization Agent.

    Returns the (potentially rewritten) SQL, human-readable notes on
    what changed, cost estimation, and index suggestions.
    """

    optimized_sql: str = Field(
        description="The optimized query. Same as input if no change needed."
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Short human-readable notes on changes made.",
    )
    estimated_cost: Literal["low", "medium", "high"]
    index_suggestions: List[str] = Field(default_factory=list)
