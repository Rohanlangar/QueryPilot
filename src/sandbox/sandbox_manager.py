# sandbox/sandbox_manager.py
"""Unified Sandbox Manager for QueryPilot.

Dispatches to:
  1. PgSandbox (Docker container with PostgreSQL 16) if Docker is available.
  2. FallbackSandbox (DuckDB/SQLite in-process) if Docker is unavailable,
     with explicit dialect difference warning.

Enforces:
  - ONE throwaway container/instance per user session
  - Read-only execution with timeouts
  - Schema replication and sample data loading with PII masking
  - Destroy on session end
"""

import logging
import threading
from typing import Dict, Any, Optional

from sandbox.pg_sandbox import (
    PgSandbox,
    DOCKER_AVAILABLE,
    get_or_create_sandbox as get_pg_sandbox,
    destroy_sandbox as destroy_pg_sandbox,
    destroy_all_sandboxes as destroy_all_pg_sandboxes,
)
from sandbox.fallback_sandbox import (
    FallbackSandbox,
    get_or_create_fallback,
    destroy_fallback,
    destroy_all_fallbacks,
)

logger = logging.getLogger(__name__)

_session_sandbox_type: Dict[str, str] = {}
_lock = threading.Lock()


class SandboxManager:
    """Orchestrates session sandboxes across Docker and Fallback engines."""

    @staticmethod
    def get_sandbox(session_id: str, connection_id: Optional[str] = None):
        """Get or initialize the appropriate sandbox for this session."""
        with _lock:
            # Check source engine dialect
            from db.connection_manager import get_connection_engine, get_connection
            try:
                source_engine = get_connection_engine(connection_id)
                conn_info = get_connection(connection_id)
                dialect = (conn_info.get("dialect", "sqlite") if conn_info else "sqlite").lower()
            except Exception:
                from db.connectors import get_engine_for_dialect
                source_engine = get_engine_for_dialect("sqlite")
                dialect = "sqlite"

            # Determine whether Docker PG container or Fallback is used
            use_docker = DOCKER_AVAILABLE and dialect in ("postgres", "postgresql")

            if use_docker:
                try:
                    sb = get_pg_sandbox(session_id, source_engine=source_engine)
                    _session_sandbox_type[session_id] = "docker"
                    return sb, "docker", None
                except Exception as e:
                    logger.warning(f"Failed to start Docker sandbox, falling back: {e}")
                    # Fallback to DuckDB/SQLite
                    fb = get_or_create_fallback(session_id, source_engine=source_engine)
                    _session_sandbox_type[session_id] = "fallback"
                    return fb, "fallback", fb._dialect_warning
            else:
                fb = get_or_create_fallback(session_id, source_engine=source_engine)
                _session_sandbox_type[session_id] = "fallback"
                warning = fb._dialect_warning if dialect in ("postgres", "postgresql") else None
                return fb, "fallback", warning

    @classmethod
    def execute(cls, session_id: str, sql: str, connection_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a query in the session's sandbox.

        Returns:
            {
                "success": bool,
                "columns": [...],
                "rows": [...],
                "row_count": int,
                "error": str | None,
                "execution_time_ms": float,
                "engine": "docker" | "fallback",
                "dialect_warning": str | None,
            }
        """
        sb, engine_type, warning = cls.get_sandbox(session_id, connection_id)
        result = sb.execute_query(sql)
        result["engine"] = engine_type
        if warning and not result.get("dialect_warning"):
            result["dialect_warning"] = warning

        # Heuristic validation: detect "looks wrong" queries
        if result["success"]:
            suspicious_issue = cls._inspect_result_quality(sql, result)
            if suspicious_issue:
                result["success"] = False
                result["error"] = f"Sandbox query semantic warning: {suspicious_issue}"

        return result

    @staticmethod
    def _inspect_result_quality(sql: str, result: Dict[str, Any]) -> Optional[str]:
        """Detect obvious semantic anomalies in query execution output."""
        sql_upper = sql.upper()
        # 1. Cartesian product check: check if row count exploded unusually or cross join without condition
        if "CROSS JOIN" in sql_upper and result.get("row_count", 0) > 1000:
            return "Unbounded CROSS JOIN detected resulting in row explosion."

        # 2. SELECT * without LIMIT on large expected sets
        if "SELECT *" in sql_upper and "LIMIT" not in sql_upper and result.get("row_count", 0) > 500:
            return "Missing LIMIT clause on wildcard query."

        return None

    @classmethod
    def destroy_session(cls, session_id: str) -> None:
        """Destroy the sandbox container/db for a session."""
        with _lock:
            stype = _session_sandbox_type.pop(session_id, None)
            if stype == "docker":
                destroy_pg_sandbox(session_id)
            else:
                destroy_fallback(session_id)

    @classmethod
    def cleanup_all(cls) -> None:
        """Tear down all active sandboxes."""
        destroy_all_pg_sandboxes()
        destroy_all_fallbacks()
        _session_sandbox_type.clear()


sandbox_manager = SandboxManager()
