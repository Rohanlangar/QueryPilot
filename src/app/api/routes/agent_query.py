"""
QueryPilot — Agent Query Routes

Direct Text-to-SQL pipeline endpoint powered by the LangGraph 5-agent pipeline:
  schema → sql_gen → validate → optimize → execute → explain

Includes dynamic database connection management endpoints.
"""

import os
import sys
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Ensure Agents package is accessible in sys.path
_agents_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

try:
    from graph.build_graph import build_graph
    from graph.state import AgentState
    from db.connectors import get_full_schema_metadata, DEFAULT_DB_FILE
    from db.seed import seed_database
    from db.connection_manager import (
        DatabaseConfig,
        test_connection,
        register_database,
        list_registered_connections,
        get_connection,
        get_connection_schema,
        delete_connection,
    )
    _graph = build_graph()
except Exception as e:
    _graph = None

router = APIRouter(tags=["Agent Pipeline"])

# In-memory query cache: {key: (timestamp, data)}
_cache: Dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 300


class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question to query against the database")
    user_id: str = Field(default="user_01", description="Identifier of the querying user")
    user_role: str = Field(default="admin", description="Role of the user for RBAC ('admin', 'analyst', 'viewer')")
    db_dialect: str = Field(default="sqlite", description="Database dialect (default: sqlite)")
    connection_id: Optional[str] = Field(default=None, description="Registered connection ID (e.g. 'prod_postgres'). Defaults to primary DB if omitted.")
    active_connections: Optional[List[str]] = Field(default=None, description="List of active connection IDs to query across simultaneously")


class QueryResponse(BaseModel):
    question: str
    final_answer: Optional[str] = None
    confidence_label: Optional[str] = None
    suggested_followups: List[str] = []
    generated_sql: Optional[str] = None
    optimized_sql: Optional[str] = None
    optimization_notes: List[str] = []
    estimated_cost: Optional[str] = None
    query_result: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = 0
    validation_passed: bool = True
    validation_errors: List[str] = []
    sources_used: Optional[List[Dict[str, Any]]] = None
    database_queries: Optional[Dict[str, str]] = None
    execution_plan: Optional[str] = None
    is_federated: Optional[bool] = False
    cached: bool = False
    execution_time_ms: float
    error: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
def execute_query(req: QueryRequest):
    """Run the multi-agent Text-to-SQL pipeline for a user question."""
    start_time = time.time()
    conn_id = req.connection_id or "default"
    norm_key = f"{conn_id}:{req.user_role}:{req.question.strip().lower()}"

    # Auto-resolve dialect if registered connection is provided
    dialect = req.db_dialect
    if req.connection_id:
        conn_info = get_connection(req.connection_id)
        if not conn_info:
            raise HTTPException(
                status_code=404,
                detail=f"Connection '{req.connection_id}' not found. Please register it via POST /connections first."
            )
        dialect = conn_info.get("dialect", req.db_dialect)

    # Check cache
    if norm_key in _cache:
        cached_time, cached_data = _cache[norm_key]
        if time.time() - cached_time < CACHE_TTL_SECONDS:
            cached_data_copy = dict(cached_data)
            cached_data_copy["cached"] = True
            cached_data_copy["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return QueryResponse(**cached_data_copy)

    if _graph is None:
        raise HTTPException(
            status_code=503,
            detail="Agent pipeline graph is initializing or unavailable.",
        )

    initial_state: AgentState = {
        "user_id": req.user_id,
        "user_role": req.user_role,
        "question": req.question,
        "db_dialect": dialect,
        "connection_id": req.connection_id,
        "active_connections": req.active_connections,
        "conversation_history": [],
        "sql_gen_attempts": 0,
    }

    try:
        final_state = _graph.invoke(initial_state)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        has_error = final_state.get("error") is not None
        validation_passed = final_state.get("validation_passed", True)

        response_data = {
            "question": req.question,
            "final_answer": final_state.get("final_answer") or final_state.get("explanation"),
            "confidence_label": final_state.get("confidence_label"),
            "suggested_followups": final_state.get("suggested_followups", []),
            "generated_sql": final_state.get("generated_sql"),
            "optimized_sql": final_state.get("optimized_sql"),
            "optimization_notes": final_state.get("optimization_notes", []),
            "estimated_cost": final_state.get("estimated_cost"),
            "query_result": final_state.get("query_result"),
            "row_count": final_state.get("row_count", 0),
            "validation_passed": validation_passed,
            "validation_errors": final_state.get("validation_errors", []),
            "sources_used": final_state.get("sources_used"),
            "database_queries": final_state.get("database_queries"),
            "execution_plan": final_state.get("execution_plan_diagram"),
            "is_federated": final_state.get("is_federated", False),
            "cached": False,
            "execution_time_ms": elapsed_ms,
            "error": final_state.get("error"),
        }

        # Cache successful queries
        if not has_error and validation_passed:
            _cache[norm_key] = (time.time(), response_data)

        return QueryResponse(**response_data)

    except Exception as e:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.get("/schema")
def get_schema():
    """Return reflected database tables and their columns."""
    try:
        return {
            "dialect": "sqlite",
            "tables": get_full_schema_metadata(),
        }
    except Exception as e:
        return {"dialect": "sqlite", "tables": {}, "error": str(e)}


@router.get("/audit-logs")
def get_audit_logs(limit: int = 50):
    """Retrieve recent query execution audit records."""
    import sqlite3
    audit_db = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "query_audit.db")
    if not os.path.exists(audit_db):
        return {"total": 0, "logs": []}
    try:
        with sqlite3.connect(audit_db) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM query_log ORDER BY id DESC LIMIT ?", (limit,))
            rows = [dict(r) for r in cur.fetchall()]
            return {"total": len(rows), "logs": rows}
    except Exception:
        return {"total": 0, "logs": []}


# ---------------------------------------------------------------------------
# Database Connection Management Endpoints
# ---------------------------------------------------------------------------

@router.post("/connections/test")
def test_db_connection(config: DatabaseConfig):
    """Test connecting to an external database (PostgreSQL, MySQL, SQLite, etc.) without registering."""
    result = test_connection(config)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/connections")
def register_db_connection(config: DatabaseConfig):
    """Register and reflect a new database connection.

    Connects to the database, extracts full schema (tables, columns, PKs, FKs, sample values),
    and caches it for instant querying via /query.
    """
    try:
        summary = register_database(config)
        return {
            "message": f"Database '{config.connection_id}' registered successfully.",
            **summary
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect and reflect schema: {str(e)}")


@router.get("/connections")
def list_connections():
    """List all registered databases and their reflected table counts."""
    return {"connections": list_registered_connections()}


@router.get("/connections/{connection_id}/schema")
def get_db_connection_schema(connection_id: str):
    """Retrieve the full reflected schema for a specific database connection."""
    schema = get_connection_schema(connection_id)
    if not schema:
        raise HTTPException(status_code=404, detail=f"No schema found for connection '{connection_id}'.")
    return {"connection_id": connection_id, "tables": schema}


@router.delete("/connections/{connection_id}")
def unregister_db_connection(connection_id: str):
    """Remove a database connection from the active registry."""
    if delete_connection(connection_id):
        return {"message": f"Connection '{connection_id}' removed successfully."}
    raise HTTPException(status_code=404, detail=f"Connection '{connection_id}' not found.")

