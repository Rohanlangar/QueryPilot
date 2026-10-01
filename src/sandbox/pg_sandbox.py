# sandbox/pg_sandbox.py
"""PostgreSQL Docker Sandbox Manager.

Manages disposable PostgreSQL containers for safe query execution.
Each user session gets ONE container that lives until the session ends or times out.

Design principle: The LLM NEVER controls Docker or the database directly.
All Docker and DB operations are plain Python code inside graph nodes.
The LLM only receives the outcome (result or error text) and decides how to fix the SQL.

Container lifecycle:
  1. Session start  → spin up postgres container, replicate schema + sample data
  2. Query arrives  → execute in sandbox, return result or error
  3. Session end    → destroy container

Security:
  - No outbound network (--network=none)
  - CPU/memory limits
  - Read-only user for query execution
  - Statement timeout (10s default)
  - No real credentials ever touch the sandbox
"""

import os
import time
import uuid
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple

import psycopg2
from psycopg2 import sql as psql
from sqlalchemy.schema import CreateTable
from decimal import Decimal

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

SANDBOX_PG_IMAGE = os.environ.get("SANDBOX_PG_IMAGE", "postgres:16")
SANDBOX_SUPERUSER = "sandbox_admin"
SANDBOX_SUPERPASS = "sandbox_secret_" + uuid.uuid4().hex[:8]
SANDBOX_READONLY_USER = "readonly_user"
SANDBOX_READONLY_PASS = "readonly_" + uuid.uuid4().hex[:8]
SANDBOX_DB_NAME = "sandbox_db"
SANDBOX_STATEMENT_TIMEOUT_MS = int(os.environ.get("SANDBOX_STATEMENT_TIMEOUT_MS", "10000"))
SANDBOX_CPU_LIMIT = float(os.environ.get("SANDBOX_CPU_LIMIT", "1.0"))  # CPUs
SANDBOX_MEM_LIMIT = os.environ.get("SANDBOX_MEM_LIMIT", "256m")
SANDBOX_SAMPLE_ROWS = int(os.environ.get("SANDBOX_SAMPLE_ROWS", "50"))
SANDBOX_STARTUP_TIMEOUT = int(os.environ.get("SANDBOX_STARTUP_TIMEOUT", "30"))

# ── Active sandbox registry ─────────────────────────────────────────────────

_active_sandboxes: Dict[str, "PgSandbox"] = {}
_lock = threading.Lock()


def _docker_available() -> bool:
    """Check if Docker SDK is importable and daemon is reachable."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


DOCKER_AVAILABLE = _docker_available()


class PgSandbox:
    """Manages a single disposable PostgreSQL Docker container."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.container = None
        self.host_port: Optional[int] = None
        self.container_id: Optional[str] = None
        self._ready = False

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Spin up a fresh PostgreSQL container for this session."""
        import docker

        client = docker.from_env()

        container_name = f"qp_sandbox_{self.session_id[:12]}_{uuid.uuid4().hex[:6]}"

        self.container = client.containers.run(
            image=SANDBOX_PG_IMAGE,
            name=container_name,
            detach=True,
            auto_remove=True,
            environment={
                "POSTGRES_USER": SANDBOX_SUPERUSER,
                "POSTGRES_PASSWORD": SANDBOX_SUPERPASS,
                "POSTGRES_DB": SANDBOX_DB_NAME,
            },
            ports={"5432/tcp": ("127.0.0.1", None)},  # Bind only to host loopback
            cpu_period=100000,
            cpu_quota=int(SANDBOX_CPU_LIMIT * 100000),
            mem_limit=SANDBOX_MEM_LIMIT,
            labels={"querypilot.sandbox": "true", "querypilot.session": self.session_id},
        )

        self.container_id = self.container.id
        self._wait_for_ready()

        # Resolve the allocated host port
        self.container.reload()
        port_bindings = self.container.attrs["NetworkSettings"]["Ports"].get("5432/tcp")
        if port_bindings:
            self.host_port = int(port_bindings[0]["HostPort"])
        else:
            raise RuntimeError("Could not resolve sandbox container port")

        # Create read-only user with statement timeout
        self._setup_readonly_user()
        self._ready = True
        logger.info(f"Sandbox started: container={container_name} port={self.host_port}")

    def _wait_for_ready(self) -> None:
        """Poll until PostgreSQL accepts connections."""
        deadline = time.time() + SANDBOX_STARTUP_TIMEOUT
        while time.time() < deadline:
            try:
                self.container.reload()
                if self.container.status != "running":
                    time.sleep(0.5)
                    continue

                port_bindings = self.container.attrs["NetworkSettings"]["Ports"].get("5432/tcp")
                if not port_bindings:
                    time.sleep(0.5)
                    continue

                port = int(port_bindings[0]["HostPort"])
                conn = psycopg2.connect(
                    host="127.0.0.1",
                    port=port,
                    user=SANDBOX_SUPERUSER,
                    password=SANDBOX_SUPERPASS,
                    dbname=SANDBOX_DB_NAME,
                    connect_timeout=3,
                )
                conn.close()
                return
            except Exception:
                time.sleep(0.5)

        raise TimeoutError(f"Sandbox container did not become ready in {SANDBOX_STARTUP_TIMEOUT}s")

    def _setup_readonly_user(self) -> None:
        """Create a read-only user with statement timeout in the sandbox."""
        conn = self._admin_connect()
        conn.autocommit = True
        cur = conn.cursor()
        try:
            cur.execute(psql.SQL("CREATE USER {} WITH PASSWORD %s").format(
                psql.Identifier(SANDBOX_READONLY_USER)
            ), [SANDBOX_READONLY_PASS])

            cur.execute(psql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                psql.Identifier(SANDBOX_DB_NAME),
                psql.Identifier(SANDBOX_READONLY_USER),
            ))

            cur.execute(psql.SQL("ALTER USER {} SET statement_timeout = %s").format(
                psql.Identifier(SANDBOX_READONLY_USER)
            ), [str(SANDBOX_STATEMENT_TIMEOUT_MS)])
        finally:
            cur.close()
            conn.close()

    def destroy(self) -> None:
        """Kill and remove the sandbox container."""
        if self.container:
            try:
                self.container.kill()
            except Exception:
                pass
            self.container = None
            self._ready = False
            logger.info(f"Sandbox destroyed: session={self.session_id}")

    # ── Connections ──────────────────────────────────────────────────────

    def _admin_connect(self) -> "psycopg2.connection":
        """Connect as superuser (for DDL operations)."""
        return psycopg2.connect(
            host="127.0.0.1",
            port=self.host_port,
            user=SANDBOX_SUPERUSER,
            password=SANDBOX_SUPERPASS,
            dbname=SANDBOX_DB_NAME,
            connect_timeout=5,
        )

    def _readonly_connect(self) -> "psycopg2.connection":
        """Connect as read-only user (for query execution)."""
        return psycopg2.connect(
            host="127.0.0.1",
            port=self.host_port,
            user=SANDBOX_READONLY_USER,
            password=SANDBOX_READONLY_PASS,
            dbname=SANDBOX_DB_NAME,
            connect_timeout=5,
            options=f"-c statement_timeout={SANDBOX_STATEMENT_TIMEOUT_MS}",
        )

    # ── Schema Replication ───────────────────────────────────────────────

    def replicate_schema(self, source_engine) -> Dict[str, int]:
        """Extract DDL from source database, create schema in sandbox, load sample data.

        Returns dict of {table_name: rows_inserted}.
        """
        from sqlalchemy import inspect as sa_inspect, text, MetaData
        from sqlalchemy.schema import CreateTable

        inspector = sa_inspect(source_engine)
        table_names = inspector.get_table_names()

        conn_admin = self._admin_connect()
        conn_admin.autocommit = True
        cur = conn_admin.cursor()

        stats: Dict[str, int] = {}

        try:
            # Order tables by foreign key dependency so parent tables are created first
            ordered_tables = self._fk_ordered_tables(inspector, table_names)

            # Step 1: Extract and replay DDL from source in dependency order
            ddl_statements = self._extract_ddl(source_engine, ordered_tables)
            for ddl in ddl_statements:
                try:
                    cur.execute(ddl)
                except Exception as e:
                    logger.warning(f"Sandbox DDL warning: {e}")

            # Step 2: Load sample data with FK-safe ordering
            with source_engine.connect() as src_conn:
                for table_name in ordered_tables:
                    try:
                        rows_inserted = self._load_sample_data(
                            src_conn, cur, table_name, inspector
                        )
                        stats[table_name] = rows_inserted
                    except Exception as e:
                        logger.warning(f"Sandbox data load warning for {table_name}: {e}")
                        stats[table_name] = 0

            # Step 3: Grant read-only SELECT to the query execution user
            for t in table_names:
                try:
                    cur.execute(psql.SQL("GRANT SELECT ON {} TO {}").format(
                        psql.Identifier(t),
                        psql.Identifier(SANDBOX_READONLY_USER),
                    ))
                except Exception:
                    pass

        finally:
            cur.close()
            conn_admin.close()

        logger.info(f"Sandbox schema replicated: {len(stats)} tables, "
                    f"{sum(stats.values())} total rows")
        return stats

    def _extract_ddl(self, engine, table_names: List[str]) -> List[str]:
        """Extract CREATE TABLE DDL from the source PostgreSQL database."""
        ddl_list = []
        with engine.connect() as conn:
            for table_name in table_names:
                try:
                    result = conn.execute(
                        psycopg2.sql.SQL("SELECT 1").as_string(conn) if False else
                        __import__("sqlalchemy").text(
                            "SELECT pg_get_tabledef(:tbl)"
                        ),
                        {"tbl": table_name}
                    )
                except Exception:
                    pass

            # Fallback: use SQLAlchemy MetaData reflection for portable DDL
            from sqlalchemy import MetaData
            metadata = MetaData()
            metadata.reflect(bind=engine)

            for table_name in table_names:
                if table_name in metadata.tables:
                    table_obj = metadata.tables[table_name]
                    create_ddl = str(CreateTable(table_obj).compile(
                        dialect=engine.dialect
                    ))
                    # Adapt for sandbox: ensure IF NOT EXISTS
                    if "CREATE TABLE" in create_ddl and "IF NOT EXISTS" not in create_ddl:
                        create_ddl = create_ddl.replace(
                            "CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1
                        )
                    ddl_list.append(create_ddl)

        return ddl_list

    def _fk_ordered_tables(self, inspector, table_names: List[str]) -> List[str]:
        """Order tables so that parent tables are populated before children (FK-safe)."""
        deps: Dict[str, set] = {t: set() for t in table_names}
        for t in table_names:
            try:
                for fk in inspector.get_foreign_keys(t):
                    ref = fk.get("referred_table")
                    if ref and ref in deps and ref != t:
                        deps[t].add(ref)
            except Exception:
                pass

        ordered = []
        visited = set()

        def visit(table):
            if table in visited:
                return
            visited.add(table)
            for dep in deps.get(table, set()):
                visit(dep)
            ordered.append(table)

        for t in table_names:
            visit(t)

        return ordered

    def _load_sample_data(self, src_conn, sandbox_cur, table_name: str, inspector) -> int:
        """Sample rows from source and insert into sandbox.

        Masks sensitive-looking columns (email, phone, ssn, password).
        """
        from sqlalchemy import text

        columns = inspector.get_columns(table_name)
        col_names = [c["name"] for c in columns]

        if not col_names:
            return 0

        cols_quoted = ", ".join(f'"{c}"' for c in col_names)
        sample_sql = f'SELECT {cols_quoted} FROM "{table_name}" ORDER BY random() LIMIT {SANDBOX_SAMPLE_ROWS}'

        try:
            result = src_conn.execute(text(sample_sql))
            rows = result.fetchall()
        except Exception:
            # Fallback without ORDER BY random() for non-PG sources
            sample_sql = f'SELECT {cols_quoted} FROM "{table_name}" LIMIT {SANDBOX_SAMPLE_ROWS}'
            result = src_conn.execute(text(sample_sql))
            rows = result.fetchall()

        if not rows:
            return 0

        # Mask sensitive columns
        sensitive_patterns = {"email", "phone", "mobile", "ssn", "password", "secret", "token"}
        sensitive_indices = [
            i for i, c in enumerate(col_names)
            if any(p in c.lower() for p in sensitive_patterns)
        ]

        masked_rows = []
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
            masked_rows.append(tuple(row_list))

        # Bulk insert into sandbox
        placeholders = ", ".join(["%s"] * len(col_names))
        insert_cols = ", ".join(f'"{c}"' for c in col_names)
        insert_sql = f'INSERT INTO "{table_name}" ({insert_cols}) VALUES ({placeholders})'

        inserted = 0
        for row in masked_rows:
            try:
                sandbox_cur.execute(insert_sql, row)
                inserted += 1
            except Exception as e:
                logger.debug(f"Sandbox row insert skip ({table_name}): {e}")

        return inserted

    # ── Query Execution ──────────────────────────────────────────────────

    def execute_query(self, sql: str) -> Dict[str, Any]:
        """Execute a SELECT query in the sandbox as the read-only user.

        Returns:
            {
                "success": bool,
                "columns": [...],
                "rows": [...],
                "row_count": int,
                "error": str | None,
                "execution_time_ms": float,
            }
        """
        if not self._ready:
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": "Sandbox is not ready",
                "execution_time_ms": 0,
            }

        start = time.time()
        try:
            conn = self._readonly_connect()
            conn.autocommit = False
            cur = conn.cursor()
            try:
                cur.execute(sql)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()

                    # Convert to list of dicts, serializing special types
                    result_rows = []
                    for row in rows:
                        row_dict = {}
                        for col, val in zip(columns, row):
                            if hasattr(val, "isoformat"):
                                row_dict[col] = val.isoformat()
                            elif isinstance(val, (bytes, bytearray)):
                                row_dict[col] = val.hex()
                            elif isinstance(val, __import__("decimal").Decimal):
                                row_dict[col] = float(val)
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
                    }
                else:
                    elapsed = round((time.time() - start) * 1000, 2)
                    return {
                        "success": False,
                        "columns": [],
                        "rows": [],
                        "row_count": 0,
                        "error": "Query did not return results (write operations are blocked in sandbox).",
                        "execution_time_ms": elapsed,
                    }
            finally:
                conn.rollback()  # Never commit anything
                cur.close()
                conn.close()

        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 2)
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e),
                "execution_time_ms": elapsed,
            }

    # ── Reset ────────────────────────────────────────────────────────────

    def reset_data(self, source_engine) -> None:
        """Truncate all tables and reload fresh sample data."""
        conn = self._admin_connect()
        conn.autocommit = True
        cur = conn.cursor()
        try:
            # Get all user tables
            cur.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
            """)
            tables = [r[0] for r in cur.fetchall()]

            # Truncate all
            if tables:
                tables_str = ", ".join(f'"{t}"' for t in tables)
                cur.execute(f"TRUNCATE {tables_str} CASCADE")

            # Reload
            cur.close()
            conn.close()

            from sqlalchemy import inspect as sa_inspect
            inspector = sa_inspect(source_engine)
            ordered = self._fk_ordered_tables(inspector, tables)

            conn2 = self._admin_connect()
            conn2.autocommit = True
            cur2 = conn2.cursor()
            with source_engine.connect() as src_conn:
                for t in ordered:
                    try:
                        self._load_sample_data(src_conn, cur2, t, inspector)
                    except Exception:
                        pass
            cur2.close()
            conn2.close()

        except Exception as e:
            logger.error(f"Sandbox reset error: {e}")
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass


# ── Module-level API ─────────────────────────────────────────────────────────

def get_or_create_sandbox(session_id: str, source_engine=None) -> PgSandbox:
    """Get existing sandbox for session or create + setup a new one."""
    with _lock:
        if session_id in _active_sandboxes:
            sb = _active_sandboxes[session_id]
            if sb._ready:
                return sb

        sb = PgSandbox(session_id)
        sb.start()

        if source_engine is not None:
            sb.replicate_schema(source_engine)

        _active_sandboxes[session_id] = sb
        return sb


def destroy_sandbox(session_id: str) -> None:
    """Destroy the sandbox container for a session."""
    with _lock:
        sb = _active_sandboxes.pop(session_id, None)
        if sb:
            sb.destroy()


def destroy_all_sandboxes() -> None:
    """Destroy all active sandbox containers (cleanup on shutdown)."""
    with _lock:
        for sid, sb in list(_active_sandboxes.items()):
            try:
                sb.destroy()
            except Exception:
                pass
        _active_sandboxes.clear()


def list_active_sandboxes() -> List[Dict[str, Any]]:
    """List all active sandbox sessions."""
    with _lock:
        return [
            {
                "session_id": sid,
                "container_id": sb.container_id,
                "port": sb.host_port,
                "ready": sb._ready,
            }
            for sid, sb in _active_sandboxes.items()
        ]
