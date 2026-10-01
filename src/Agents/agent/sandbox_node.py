# agent/sandbox_node.py
"""Sandbox Execution Node for LangGraph Text-to-SQL Pipeline.

Executes queries in an isolated Docker (or Fallback) container before they can
ever be returned or executed on the real database.
If execution fails or results look wrong, records error so the pipeline can
route back to sql_gen for self-healing repair.
"""

import logging
from typing import Dict, Any

from sandbox.sandbox_manager import sandbox_manager

logger = logging.getLogger(__name__)


def sandbox_node(state: dict) -> dict:
    """LangGraph node: execute candidate SQL in an isolated sandbox.

    Reads:
        state.get("optimized_sql") or state.get("generated_sql")
        state.get("session_id") or state.get("user_id")
        state.get("connection_id")

    Returns partial state update:
        {
            "sandbox_executed": True,
            "sandbox_passed": bool,
            "sandbox_result": list,
            "sandbox_error": str | None,
            "sandbox_engine": str,
            "sandbox_dialect_warning": str | None,
            "validation_errors": list,
        }
    """
    sql = state.get("optimized_sql") or state.get("generated_sql", "").strip()
    session_id = state.get("session_id") or f"sess_{state.get('user_id', 'anon')}_{state.get('connection_id', 'default')}"
    connection_id = state.get("connection_id")

    if not sql:
        return {
            "sandbox_executed": True,
            "sandbox_passed": False,
            "sandbox_result": [],
            "sandbox_error": "No SQL query provided for sandbox execution.",
            "sandbox_engine": "none",
            "sandbox_dialect_warning": None,
        }

    try:
        res = sandbox_manager.execute(session_id=session_id, sql=sql, connection_id=connection_id)
        if res.get("success"):
            return {
                "sandbox_executed": True,
                "sandbox_passed": True,
                "sandbox_result": res.get("rows", []),
                "sandbox_error": None,
                "sandbox_engine": res.get("engine", "sandbox"),
                "sandbox_dialect_warning": res.get("dialect_warning"),
                "execution_error": None,
            }
        else:
            err = res.get("error", "Unknown sandbox execution error")
            existing_errors = list(state.get("validation_errors") or [])
            existing_errors.append(f"Sandbox runtime error: {err}")
            return {
                "sandbox_executed": True,
                "sandbox_passed": False,
                "sandbox_result": [],
                "sandbox_error": err,
                "sandbox_engine": res.get("engine", "sandbox"),
                "sandbox_dialect_warning": res.get("dialect_warning"),
                "validation_errors": existing_errors,
            }
    except Exception as e:
        err = str(e)
        logger.error(f"Sandbox node execution failure: {err}")
        existing_errors = list(state.get("validation_errors") or [])
        existing_errors.append(f"Sandbox internal error: {err}")
        return {
            "sandbox_executed": True,
            "sandbox_passed": False,
            "sandbox_result": [],
            "sandbox_error": err,
            "sandbox_engine": "unknown",
            "sandbox_dialect_warning": None,
            "validation_errors": existing_errors,
        }
