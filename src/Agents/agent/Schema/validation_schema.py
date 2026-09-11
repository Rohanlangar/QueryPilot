# agent/Schema/validation_schema.py
from pydantic import BaseModel
from typing import List, Optional, Dict


class ValidationResult(BaseModel):
    """Structured result of the deterministic Validation Agent.

    Validation is NOT an LLM call — it uses sqlparse + schema lookup + RBAC.
    This schema exists so the node's return shape is typed and consistent
    with the rest of the graph.
    """

    passed: bool
    errors: List[str] = []
    security_incident: Optional[dict] = None
