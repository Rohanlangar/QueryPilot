"""Main FastAPI application for QueryPilot Text-to-SQL system.

Exposes:
  - POST /query: Main multi-agent Text-to-SQL endpoint
  - GET /health: Service health check
  - GET /schema: Currently reflected database schema
  - GET /audit-logs: Query execution audit trail
"""

import sys
import os
import time
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime

# Ensure Agents package is accessible in sys.path
_agents_dir = os.path.join(os.path.dirname(__file__), "Agents")
if _agents_dir not in sys.path:
    sys.path.insert(0, _agents_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from graph.build_graph import build_graph
from graph.state import AgentState
from db.connectors import get_full_schema_metadata, DEFAULT_DB_FILE
from db.seed import seed_database

# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title="QueryPilot API",
    description="Multi-Agent Text-to-SQL System using LangGraph and Local Qwen LLMs via Ollama",
    version="1.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compiled LangGraph pipeline instance
_graph = None

# Audit DB path
AUDIT_DB_PATH = os.path.join(os.path.dirname(__file__), "query_audit.db")

# Simple memory cache: {normalized_question: (timestamp, response_data)}
_cache: Dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question to query against the database")
    user_id: str = Field(default="user_01", description="Identifier of the querying user")
    user_role: str = Field(default="admin", description="Role of the user for RBAC ('admin', 'analyst', 'viewer')")
    db_dialect: str = Field(default="sqlite", description="Database dialect (default: sqlite)")


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
    cached: bool = False
    execution_time_ms: float
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Audit Logger Setup
# ---------------------------------------------------------------------------

def init_audit_db():
    """Create audit table if it does not exist."""
    with sqlite3.connect(AUDIT_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_role TEXT NOT NULL,
                question TEXT NOT NULL,
                generated_sql TEXT,
                optimized_sql TEXT,
                execution_time_ms REAL NOT NULL,
                confidence_label TEXT,
                status TEXT NOT NULL,
                error TEXT
            )
        """)
        conn.commit()


def log_query_audit(
    user_id: str,
    user_role: str,
    question: str,
    generated_sql: Optional[str],
    optimized_sql: Optional[str],
    execution_time_ms: float,
    confidence_label: Optional[str],
    status: str,
    error: Optional[str] = None,
):
    """Record query execution to audit table."""
    try:
        with sqlite3.connect(AUDIT_DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO query_log (
                    timestamp, user_id, user_role, question,
                    generated_sql, optimized_sql, execution_time_ms,
                    confidence_label, status, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    user_id,
                    user_role,
                    question,
                    generated_sql,
                    optimized_sql,
                    execution_time_ms,
                    confidence_label,
                    status,
                    error,
                ),
            )
            conn.commit()
    except Exception as e:
        print(f"[Audit Log Error] Failed to write audit record: {e}")


# ---------------------------------------------------------------------------
# Lifecycle Events
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    """Ensure demo database is seeded, schema is cached, and graph is built."""
    global _graph
    print("Initializing QueryPilot...")

    # 1. Seed demo database if missing
    if not os.path.exists(DEFAULT_DB_FILE):
        print("Demo database not found. Seeding company.db...")
        seed_database(DEFAULT_DB_FILE)

    # 2. Warm up reflected schema metadata cache
    metadata = get_full_schema_metadata()
    print(f"Schema metadata loaded with {len(metadata)} tables: {list(metadata.keys())}")

    # 3. Setup audit database
    init_audit_db()

    # 4. Compile the LangGraph pipeline
    _graph = build_graph()
    print("LangGraph pipeline compiled successfully.")


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "QueryPilot Text-to-SQL API",
        "db_exists": os.path.exists(DEFAULT_DB_FILE),
        "graph_ready": _graph is not None,
    }


@app.get("/schema")
def get_schema():
    """Return all reflected database tables and their columns."""
    return {
        "dialect": "sqlite",
        "tables": get_full_schema_metadata(),
    }


@app.get("/audit-logs")
def get_audit_logs(limit: int = 50):
    """Retrieve recent query execution audit records."""
    init_audit_db()
    with sqlite3.connect(AUDIT_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM query_log ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        return {"total": len(rows), "logs": rows}


@app.post("/query", response_model=QueryResponse)
def execute_query(req: QueryRequest):
    """Run the multi-agent Text-to-SQL pipeline for a user question.

    Steps:
      1. Check in-memory semantic TTL cache.
      2. If miss, run LangGraph pipeline.
      3. Log audit trail.
      4. Return structured response.
    """
    start_time = time.time()
    norm_key = f"{req.user_role}:{req.question.strip().lower()}"

    # Check cache
    if norm_key in _cache:
        cached_time, cached_data = _cache[norm_key]
        if time.time() - cached_time < CACHE_TTL_SECONDS:
            cached_data_copy = dict(cached_data)
            cached_data_copy["cached"] = True
            cached_data_copy["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return QueryResponse(**cached_data_copy)

    initial_state: AgentState = {
        "user_id": req.user_id,
        "user_role": req.user_role,
        "question": req.question,
        "db_dialect": req.db_dialect,
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
            "cached": False,
            "execution_time_ms": elapsed_ms,
            "error": final_state.get("error"),
        }

        # Cache successful queries
        if not has_error and validation_passed:
            _cache[norm_key] = (time.time(), response_data)

        # Audit logging
        status = "ERROR" if has_error or not validation_passed else "SUCCESS"
        log_query_audit(
            user_id=req.user_id,
            user_role=req.user_role,
            question=req.question,
            generated_sql=final_state.get("generated_sql"),
            optimized_sql=final_state.get("optimized_sql"),
            execution_time_ms=elapsed_ms,
            confidence_label=final_state.get("confidence_label"),
            status=status,
            error=final_state.get("error"),
        )

        return QueryResponse(**response_data)

    except Exception as e:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        error_msg = str(e)
        log_query_audit(
            user_id=req.user_id,
            user_role=req.user_role,
            question=req.question,
            generated_sql=None,
            optimized_sql=None,
            execution_time_ms=elapsed_ms,
            confidence_label=None,
            status="FAILED",
            error=error_msg,
        )
        raise HTTPException(status_code=500, detail=f"Pipeline error: {error_msg}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
