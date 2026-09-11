"""
QueryPilot — Multi-DB Connection Manager

Handles creation, pooling, testing, and lifecycle management of
external database connections. Supports PostgreSQL, MySQL, MSSQL, and Oracle.
Credentials are encrypted at rest using Fernet.
"""

import time
import json
import logging
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from app.core.security import decrypt_credential
from app.models.connection import Connection

logger = logging.getLogger(__name__)


# ── Dialect Mapping ───────────────────────────────────────────
DIALECT_MAP = {
    "postgresql": "postgresql+asyncpg",
    "mysql": "mysql+aiomysql",
    "mssql": "mssql+pyodbc",
    "oracle": "oracle+cx_oracle",
}

# Default ports per database type
DEFAULT_PORTS = {
    "postgresql": 5432,
    "mysql": 3306,
    "mssql": 1433,
    "oracle": 1521,
}


class ConnectionManager:
    """
    Manages a pool of async SQLAlchemy engines for external database
    connections. Each connection gets its own engine with connection pooling.
    """

    def __init__(self):
        self._engines: Dict[str, AsyncEngine] = {}

    def _build_url_from_params(
        self,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        ssl_enabled: bool = False,
    ) -> str:
        """Build a SQLAlchemy connection URL from individual parameters."""
        dialect = DIALECT_MAP.get(db_type)
        if not dialect:
            raise ValueError(f"Unsupported database type: {db_type}")

        # MSSQL requires special handling for pyodbc
        if db_type == "mssql":
            driver = "ODBC+Driver+18+for+SQL+Server"
            return (
                f"{dialect}://{username}:{password}"
                f"@{host}:{port}/{database_name}"
                f"?driver={driver}&TrustServerCertificate=yes"
            )

        # Oracle uses SID-based connection format
        if db_type == "oracle":
            return (
                f"{dialect}://{username}:{password}"
                f"@{host}:{port}/{database_name}"
            )

        # PostgreSQL and MySQL — standard URL format
        url = f"{dialect}://{username}:{password}@{host}:{port}/{database_name}"

        # Add SSL if enabled
        if ssl_enabled:
            if db_type == "postgresql":
                url += "?ssl=require"
            elif db_type == "mysql":
                url += "?ssl=true"

        return url

    def _build_url(self, conn: Connection) -> str:
        """Build a SQLAlchemy connection URL from a Connection model."""
        password = decrypt_credential(conn.encrypted_password)
        return self._build_url_from_params(
            db_type=conn.db_type,
            host=conn.host,
            port=conn.port,
            database_name=conn.database_name,
            username=conn.username,
            password=password,
            ssl_enabled=conn.ssl_enabled,
        )

    async def create_engine(self, conn: Connection) -> AsyncEngine:
        """
        Create and cache an async SQLAlchemy engine for the given connection.
        Uses connection pooling with sensible defaults.
        """
        if conn.id in self._engines:
            return self._engines[conn.id]

        url = self._build_url(conn)

        # Parse extra params if provided
        engine_kwargs = {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,  # Recycle connections every 30 min
            "echo": False,
        }

        if conn.extra_params:
            try:
                extra = json.loads(conn.extra_params)
                engine_kwargs.update(extra)
            except json.JSONDecodeError:
                logger.warning(f"Invalid extra_params JSON for connection {conn.id}")

        engine = create_async_engine(url, **engine_kwargs)
        self._engines[conn.id] = engine
        logger.info(f"Created engine for connection '{conn.name}' ({conn.db_type})")
        return engine

    async def test_connection(self, conn: Connection) -> dict:
        """
        Test connectivity to an external database.
        Returns {success: bool, message: str, latency_ms: float}.
        """
        try:
            start = time.perf_counter()
            engine = await self.create_engine(conn)
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000

            return {
                "success": True,
                "message": f"Connected to {conn.db_type}://{conn.host}:{conn.port}/{conn.database_name}",
                "latency_ms": round(latency, 2),
            }
        except Exception as e:
            # Clean up failed engine from cache
            await self.close_connection(conn.id)
    async def test_raw_connection(
        self,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        ssl_enabled: bool = False,
        extra_params: Optional[str] = None,
    ) -> dict:
        """
        Test connectivity using raw parameters before saving.
        Returns {success: bool, message: str, latency_ms: float}.
        """
        engine = None
        try:
            url = self._build_url_from_params(
                db_type=db_type,
                host=host,
                port=port,
                database_name=database_name,
                username=username,
                password=password,
                ssl_enabled=ssl_enabled,
            )
            engine_kwargs = {"pool_timeout": 10}
            if extra_params:
                try:
                    extra = json.loads(extra_params)
                    engine_kwargs.update(extra)
                except json.JSONDecodeError:
                    pass

            engine = create_async_engine(url, **engine_kwargs)
            start = time.perf_counter()
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000

            return {
                "success": True,
                "message": f"Successfully connected to {db_type}://{host}:{port}/{database_name}",
                "latency_ms": round(latency, 2),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "latency_ms": None,
            }
        finally:
            if engine:
                await engine.dispose()

    def get_engine(self, connection_id: str) -> Optional[AsyncEngine]:
        """Retrieve a cached engine by connection ID."""
        return self._engines.get(connection_id)

    async def close_connection(self, connection_id: str):
        """Close and remove a cached engine."""
        engine = self._engines.pop(connection_id, None)
        if engine:
            await engine.dispose()
            logger.info(f"Disposed engine for connection {connection_id}")

    async def close_all(self):
        """Dispose all cached engines. Called on shutdown."""
        for conn_id in list(self._engines.keys()):
            await self.close_connection(conn_id)
        logger.info("All external database connections closed")


# Singleton instance
connection_manager = ConnectionManager()
