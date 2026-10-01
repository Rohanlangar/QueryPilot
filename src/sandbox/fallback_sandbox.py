# sandbox/fallback_sandbox.py
"""DuckDB-based fallback sandbox for when Docker is unavailable.

DuckDB has excellent PostgreSQL dialect compatibility, making it a
strong fallback for validating SQL before real execution.

IMPORTANT: This fallback will clearly warn the user that dialect
differences may apply.
"""

import os
import time
import uuid
import logging
import tempfile
import threading
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Try to import duckdb; if unavailable, use sqlite3 as last resort
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

import sqlite3

_active_fallbacks: Dict[str, "FallbackSandbox"] = {}
_lock = threading.Lock()

FALLBACK_SAMPLE_ROWS = int(os.environ.get("SANDBOX_SAMPLE_ROWS", "50"))
FALLBACK_STATEMENT_TIMEOUT_S = int(os.environ.get("SANDBOX_STATEMENT_TIMEOUT_MS", "10000")) / 1000


class FallbackSandbox:
    """In-process DuckDB/SQLite sandbox — no Docker required.

    Provides the same interface as PgSandbox.execute_query().
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._db_path = os.path.join(
            tempfile.gettempdir(),
            f"qp_sandbox_{session_id[:12]}_{uuid.uuid4().hex[:6]}.db"
        )
        self._conn = None
        self._ready = False
        self._engine_type = "duckdb" if DUCKDB_AVAILABLE else "sqlite"
        self._dialect_warning = (
            f"⚠️  Docker unavailable — using {self._engine_type} fallback sandbox. "
            f"Some PostgreSQL-specific syntax (e.g., ::type casts, ILIKE, ARRAY ops) "
            f"may behave differently."
        )

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Initialize the in-process database."""
        if DUCKDB_AVAILABLE:
            self._conn = duckdb.connect(self._db_path)
            # Enable PG-compatible mode
            try:
                self._conn.execute("SET pg_experimental_types = true")
            except Exception:
                pass
        else:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)

        self._ready = True
        logger.info(f"Fallback sandbox started: engine={self._engine_type} "
                    f"session={self.session_id}")

    def destroy(self) -> None:
        """Close connection and remove database file."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

        if os.path.exists(self._db_path):
            try:
                os.remove(self._db_path)
            except Exception:
                pass

        self._ready = False
        logger.info(f"Fallback sandbox destroyed: session={self.session_id}")

    # ── Schema Replication ───────────────────────────────────────────────

    def replicate_schema(self, source_engine) -> Dict[str, int]:
        """Replicate schema from source database into fallback sandbox."""
        from sqlalchemy import inspect as sa_inspect, text, MetaData
        from sqlalchemy.schema import CreateTable

        inspector = sa_inspect(source_engine)
        table_names = inspector.get_table_names()

        stats: Dict[str, int] = {}

        # Reflect the full metadata
        metadata = MetaData()
        metadata.reflect(bind=source_engine)

        for table_name in table_names:
            try:
                # Generate CREATE TABLE DDL
                if table_name in metadata.tables:
                    table_obj = metadata.tables[table_name]
                    create_ddl = str(CreateTable(table_obj).compile(
                        dialect=source_engine.dialect
                    ))

                    # Adapt PostgreSQL DDL to DuckDB/SQLite compatible DDL
                    adapted_ddl = self._adapt_ddl(create_ddl, table_name)

                    try:
                        if DUCKDB_AVAILABLE:
                            self._conn.execute(adapted_ddl)
                        else:
                            self._conn.execute(adapted_ddl)
                            self._conn.commit()
                    except Exception as e:
                        logger.warning(f"Fallback DDL error for {table_name}: {e}")
                        stats[table_name] = 0
                        continue

                # Load sample data
                rows_inserted = self._load_sample_data(source_engine, table_name, inspector)
                stats[table_name] = rows_inserted

            except Exception as e:
                logger.warning(f"Fallback schema replication error for {table_name}: {e}")
                stats[table_name] = 0

        logger.info(f"Fallback sandbox schema replicated: {len(stats)} tables, "
                    f"{sum(stats.values())} total rows")
        return stats

    def _adapt_ddl(self, ddl: str, table_name: str) -> str:
        """Adapt PostgreSQL DDL for DuckDB/SQLite compatibility."""
        import re

        # Add IF NOT EXISTS
        if "CREATE TABLE" in ddl and "IF NOT EXISTS" not in ddl:
            ddl = ddl.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1)

        # Common PostgreSQL type mappings for SQLite
        if not DUCKDB_AVAILABLE:
            type_mappings = {
                r"SERIAL": "INTEGER",
                r"BIGSERIAL": "INTEGER",
                r"SMALLSERIAL": "INTEGER",
                r"UUID": "TEXT",
                r"JSONB?": "TEXT",
                r"TIMESTAMP\s*(WITH\s*TIME\s*ZONE)?": "TEXT",
                r"TIMESTAMPTZ": "TEXT",
                r"INTERVAL": "TEXT",
                r"INET": "TEXT",
                r"CIDR": "TEXT",
                r"MACADDR": "TEXT",
                r"ARRAY": "TEXT",
                r"BYTEA": "BLOB",
            }
            for pg_type, fallback_type in type_mappings.items():
                ddl = re.sub(pg_type, fallback_type, ddl, flags=re.IGNORECASE)

        # Remove PostgreSQL-specific clauses
        ddl = re.sub(r"DEFAULT\s+nextval\([^)]+\)", "", ddl, flags=re.IGNORECASE)
        ddl = re.sub(r"WITH\s*\([^)]*\)", "", ddl, flags=re.IGNORECASE)  # Remove storage params

        return ddl

    def _load_sample_data(self, source_engine, table_name: str, inspector) -> int:
        """Load sample data from source into fallback sandbox."""
        from sqlalchemy import text

        columns = inspector.get_columns(table_name)
        col_names = [c["name"] for c in columns]

        if not col_names:
            return 0

        cols_quoted = ", ".join(f'"{c}"' for c in col_names)

        with source_engine.connect() as conn:
            try:
                result = conn.execute(text(
                    f'SELECT {cols_quoted} FROM "{table_name}" LIMIT {FALLBACK_SAMPLE_ROWS}'
                ))
                rows = result.fetchall()
            except Exception:
                return 0

        if not rows:
            return 0

        # Mask sensitive columns
        sensitive_patterns = {"email", "phone", "mobile", "ssn", "password", "secret", "token"}
        sensitive_indices = [
            i for i, c in enumerate(col_names)
            if any(p in c.lower() for p in sensitive_patterns)
        ]

        inserted = 0
        for row in rows:
            row_list = list(row)
            for idx in sensitive_indices:
                val = row_list[idx]
                if isinstance(val, str):
                    if "@" in val:
                        row_list[idx] = f"user{hash(val) % 9999}@sandbox.local"
                    elif val.replace("-", "").replace(" ", "").isdigit():
                        row_list[idx] = "555-000-0000"
                    else:
                        row_list[idx] = "[MASKED]"

            placeholders = ", ".join(["?"] * len(col_names))
            insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'

            try:
                if DUCKDB_AVAILABLE:
                    self._conn.execute(insert_sql, row_list)
                else:
                    self._conn.execute(insert_sql, row_list)
                    self._conn.commit()
                inserted += 1
            except Exception as e:
                logger.debug(f"Fallback row insert skip ({table_name}): {e}")

        return inserted

    # ── Query Execution ──────────────────────────────────────────────────

    def execute_query(self, sql: str) -> Dict[str, Any]:
        """Execute a query in the fallback sandbox.

        Returns same structure as PgSandbox.execute_query().
        """
        if not self._ready or not self._conn:
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": "Fallback sandbox is not ready",
                "execution_time_ms": 0,
                "dialect_warning": self._dialect_warning,
            }

        start = time.time()
        try:
            if DUCKDB_AVAILABLE:
                result = self._conn.execute(sql)
                if result.description:
                    columns = [desc[0] for desc in result.description]
                    raw_rows = result.fetchall()
                    result_rows = []
                    for row in raw_rows:
                        row_dict = {}
                        for col, val in zip(columns, row):
                            if hasattr(val, "isoformat"):
                                row_dict[col] = val.isoformat()
                            elif isinstance(val, (bytes, bytearray)):
                                row_dict[col] = val.hex()
                            else:
                                row_dict[col] = val
                        result_rows.append(row_dict)

                    elapsed = round((time.time() - start) * 1000, 2)
                    return {
                        "success": True,
                        "columns": columns,
                        "rows": result_rows,
                        "row_count": len(result_rows),
                        "error": None,
                        "execution_time_ms": elapsed,
                        "dialect_warning": self._dialect_warning,
                    }
            else:
                cursor = self._conn.cursor()
                cursor.execute(sql)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    raw_rows = cursor.fetchall()
                    result_rows = []
                    for row in raw_rows:
                        row_dict = {}
                        for col, val in zip(columns, row):
                            row_dict[col] = val
                        result_rows.append(row_dict)

                    elapsed = round((time.time() - start) * 1000, 2)
                    return {
                        "success": True,
                        "columns": columns,
                        "rows": result_rows,
                        "row_count": len(result_rows),
                        "error": None,
                        "execution_time_ms": elapsed,
                        "dialect_warning": self._dialect_warning,
                    }

            elapsed = round((time.time() - start) * 1000, 2)
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": "Query did not return results.",
                "execution_time_ms": elapsed,
                "dialect_warning": self._dialect_warning,
            }

        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e),
                "execution_time_ms": elapsed,
                "dialect_warning": self._dialect_warning,
            }


# ── Module-level API ─────────────────────────────────────────────────────────

def get_or_create_fallback(session_id: str, source_engine=None) -> FallbackSandbox:
    """Get existing fallback sandbox for session or create a new one."""
    with _lock:
        if session_id in _active_fallbacks:
            fb = _active_fallbacks[session_id]
            if fb._ready:
                return fb

        fb = FallbackSandbox(session_id)
        fb.start()

        if source_engine is not None:
            fb.replicate_schema(source_engine)

        _active_fallbacks[session_id] = fb
        return fb


def destroy_fallback(session_id: str) -> None:
    """Destroy fallback sandbox for a session."""
    with _lock:
        fb = _active_fallbacks.pop(session_id, None)
        if fb:
            fb.destroy()


def destroy_all_fallbacks() -> None:
    """Destroy all active fallback sandboxes."""
    with _lock:
        for sid, fb in list(_active_fallbacks.items()):
            try:
                fb.destroy()
            except Exception:
                pass
        _active_fallbacks.clear()
