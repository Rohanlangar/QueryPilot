# agent/Schema/sql_gen_schema.py
from pydantic import BaseModel, Field
from typing import List


class SQLGenerationOutput(BaseModel):
    """Structured output for the SQL Generation Agent.

    Contains the generated SQL query and any assumptions made
    about ambiguous column or table meaning.
    """

    sql: str = Field(
        description="The generated SQL query only. No markdown fences, no comments."
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Any assumptions made about ambiguous column or table meaning.",
    )
