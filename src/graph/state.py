# graph/state.py
"""LangGraph state definition for the Text-to-SQL pipeline.

Supports both single-database queries and multi-database federated SQL queries
across independent microservices databases.
Using TypedDict with total=False so nodes can return partial updates.
"""

from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict, total=False):
    """Complete state schema for the multi-agent Text-to-SQL & Federation graph.

    Fields are grouped by the pipeline stage that produces them.
    """

    # ── Input fields (set by caller / orchestrator) ───────────────────
    user_id: str
    user_role: str
    question: str
    connection_id: Optional[str]               # Optional single DB ID (legacy / override)
    active_connections: Optional[List[str]]     # List of active connection IDs to query
    conversation_history: List[Dict]            # Multi-turn context preservation
    sql_gen_attempts: int

    # ── Schema Discovery Agent output ─────────────────────────────────
    unified_schema: Dict[str, Any]             # Full schema catalog across all active DBs
    relevant_schema: Dict[str, Any]            # Flattened or selected relevant tables
    cross_db_relationships: List[Dict[str, Any]] # Inferred cross-database joins (e.g. product_id)
    db_dialect: str                            # Default or primary dialect

    # ── Query Planning Agent output ───────────────────────────────────
    query_plan: Dict[str, Any]                 # Planning decision (is_federated, dbs, tables, join keys)
    is_federated: bool                         # True if question requires >1 database

    # ── SQL Generation Agent output ───────────────────────────────────
    database_queries: Dict[str, str]           # {db_id: generated_sql} per database
    generated_sql: str                         # Formatted SQL query (or primary single query)

    # ── Validation Agent output ───────────────────────────────────────
    validation_passed: bool
    validation_errors: List[str]
    validation_details: Dict[str, Any]         # Per-database validation results

    # ── Optimization Agent output ─────────────────────────────────────
    optimized_sql: str
    optimization_notes: List[str]
    estimated_cost: Optional[str]

    # ── Post-Optimization Validation output ───────────────────────────
    post_optimization_validation_passed: bool
    post_optimization_validation_errors: List[str]

    # ── Query Execution Agent output ──────────────────────────────────
    database_results: Dict[str, Any]           # {db_id: {"columns": [...], "rows": [...], "row_count": N}}
    execution_error: Optional[str]

    # ── Federation / Join Agent output ────────────────────────────────
    federated_result: Optional[Dict[str, Any]] # Unified joined data
    query_result: Optional[List[Dict]]         # Standardized unified rows
    row_count: Optional[int]                   # Total unified row count
    execution_plan_diagram: Optional[str]      # ASCII / visual execution plan diagram

    # ── Explanation Agent output ──────────────────────────────────────
    explanation: str
    confidence_label: str
    confidence_reason: Optional[str]
    suggested_followups: List[str]
    sources_used: List[Dict[str, Any]]         # [{database: ..., tables: [...]}]

    # ── Final output ──────────────────────────────────────────────────
    final_answer: Optional[str]
    error: Optional[str]
