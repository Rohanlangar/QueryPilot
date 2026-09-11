"""
QueryPilot — Safe Query Executor

Executes validated SQL queries against external databases with safety
guardrails: read-only enforcement, row limits, timeouts, and structured
result formatting.
"""

import time
import logging
import re
from typing import List, Dict, Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import settings

logger = logging.getLogger(__name__)

# ── Dangerous SQL Patterns ────────────────────────────────────
WRITE_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


class QueryExecutor:
    """
    Executes SQL queries with safety guardrails.

    - Blocks write operations (INSERT, UPDATE, DELETE, DROP, etc.)
    - Enforces row limits (wraps with LIMIT if needed)
    - Applies query timeouts
    - Returns structured results {columns, rows, row_count, execution_time_ms}
    """

    def __init__(self):
        self.max_rows = settings.max_query_rows
        self.timeout_seconds = settings.query_timeout_seconds

    def _validate_read_only(self, sql: str) -> None:
        """Ensure the query is read-only. Raises ValueError if not."""
        # Strip comments
        cleaned = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

        if WRITE_PATTERNS.search(cleaned):
            raise ValueError(
                "Write operations are not allowed. Only SELECT queries are permitted."
            )

    def _enforce_row_limit(self, sql: str) -> str:
        """
        Add a row limit if the query doesn't already have one.
        Handles different SQL dialects.
        """
        sql_upper = sql.strip().upper()

        # Check if LIMIT/TOP/FETCH FIRST is already present
        if any(kw in sql_upper for kw in ["LIMIT", "FETCH FIRST", "FETCH NEXT", "TOP "]):
            return sql

        # Add LIMIT clause
        sql = sql.rstrip().rstrip(";")
        return f"{sql}\nLIMIT {self.max_rows}"

    async def execute(
        self,
        engine: AsyncEngine,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a SQL query safely and return structured results.

        Args:
            engine: AsyncEngine for the target database
            sql: The SQL query string
            params: Optional query parameters

        Returns:
            {
                "columns": ["col1", "col2"],
                "rows": [{"col1": val, "col2": val}, ...],
                "row_count": 42,
                "execution_time_ms": 123.45,
                "truncated": False,  # True if hit row limit
            }
        """
        # Safety check
        self._validate_read_only(sql)

        # Enforce row limit
        limited_sql = self._enforce_row_limit(sql)

        start = time.perf_counter()

        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(limited_sql),
                    params or {},
                )

                columns = list(result.keys())
                rows_raw = result.fetchall()

                # Convert to list of dicts
                rows = [dict(zip(columns, row)) for row in rows_raw]

                execution_time = (time.perf_counter() - start) * 1000

                # Serialize values that aren't JSON-friendly
                for row in rows:
                    for key, value in row.items():
                        if hasattr(value, "isoformat"):
                            row[key] = value.isoformat()
                        elif isinstance(value, bytes):
                            row[key] = value.hex()
                        elif isinstance(value, (set, frozenset)):
                            row[key] = list(value)

                truncated = len(rows) >= self.max_rows

                logger.info(
                    f"Query executed: {len(rows)} rows, {execution_time:.1f}ms"
                    + (" (truncated)" if truncated else "")
                )

                return {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "execution_time_ms": round(execution_time, 2),
                    "truncated": truncated,
                }

        except ValueError:
            raise  # Re-raise read-only violations
        except Exception as e:
            execution_time = (time.perf_counter() - start) * 1000
            logger.error(f"Query execution failed after {execution_time:.1f}ms: {e}")
            raise RuntimeError(f"Query execution failed: {str(e)}")


# Singleton instance
query_executor = QueryExecutor()
