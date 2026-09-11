# graph/state.py
"""LangGraph state definition for the Text-to-SQL pipeline.

All fields used across any node in the graph are declared here.
Using TypedDict with total=False so nodes can return partial updates.
"""

from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict, total=False):
    """Complete state schema for the multi-agent Text-to-SQL graph.

    Fields are grouped by the pipeline stage that produces them.
    """

    # ── Input fields (set by the caller) ───────────────────────────────
    user_id: str
    user_role: str
    question: str
    connection_id: Optional[str]
    conversation_history: List[Dict]

    # ── Schema Agent output ────────────────────────────────────────────
    relevant_schema: Dict[str, Any]
    db_dialect: str

    # ── SQL Generation Agent output ────────────────────────────────────
    generated_sql: str
    sql_gen_attempts: int

    # ── Validation Agent output ────────────────────────────────────────
    validation_passed: bool
    validation_errors: List[str]

    # ── Optimization Agent output ──────────────────────────────────────
    optimized_sql: str
    optimization_notes: List[str]
    estimated_cost: Optional[str]

    # ── Post-Optimization Validation output ───────────────────────────
    post_optimization_validation_passed: bool
    post_optimization_validation_errors: List[str]

    # ── Query Execution output ─────────────────────────────────────────
    query_result: Optional[List[Dict]]
    row_count: Optional[int]
    execution_error: Optional[str]

    # ── Explanation Agent output ───────────────────────────────────────
    explanation: str
    confidence_label: str
    suggested_followups: List[str]

    # ── Final output ───────────────────────────────────────────────────
    final_answer: Optional[str]
    error: Optional[str]
