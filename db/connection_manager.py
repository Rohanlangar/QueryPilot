"""Database Connection Manager for QueryPilot.

Allows users to dynamically connect to any database (PostgreSQL, MySQL, SQLite, MSSQL, etc.)
by providing connection parameters or a raw connection string.

Features:
- Validates and tests database connectivity
- Deeply inspects and extracts tables, columns, types, PKs, FKs, and categorical sample values
- Manages an in-memory registry of active database connections and cached schemas
- Provides the target engine and reflected schema to the LangGraph pipeline
"""

import os
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

# In-memory registry of active connections: {connection_id: {"engine": Engine, "config": DatabaseConfig, "schema": dict}}
_ACTIVE_CONNECTIONS: Dict[str, Dict[str, Any]] = {}


class DatabaseConfig(BaseModel):
    """Configuration model for connecting to an external database."""
    connection_id: str = Field(..., description="Unique identifier for this connection, e.g. 'prod_postgres'")
    db_type: str = Field(default="sqlite", description="Database dialect: 'postgresql', 'mysql', 'sqlite', 'mssql', etc.")
    host: Optional[str] = Field(default=None, description="Host address, e.g. 'localhost' or 'db.example.com'")
    port: Optional[int] = Field(default=None, description="Port number, e.g. 5432 for Postgres, 3306 for MySQL")
    database: str = Field(..., description="Database name (or file path for SQLite)")
    username: Optional[str] = Field(default=None, description="Database username")
    password: Optional[str] = Field(default=None, description="Database password")
    ssl_mode: Optional[str] = Field(default=None, description="SSL mode if applicable, e.g. 'require'")
    connection_url: Optional[str] = Field(default=None, description="Direct SQLAlchemy connection URL (overrides individual fields if provided)")


def build_connection_url(config: DatabaseConfig) -> str:
    """Build a standard SQLAlchemy connection URL from config parameters."""
    if config.connection_url and config.connection_url.strip():
        return config.connection_url.strip()

    db_type = (config.db_type or "sqlite").lower().strip()

    if db_type == "sqlite":
        db_path = config.database
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        return f"sqlite:///{db_path}"

    user = quote_plus(config.username or "")
    password = quote_plus(config.password or "")
    auth_part = f"{user}:{password}@" if user or password else ""
    host = config.host or "localhost"

    if db_type in ("postgres", "postgresql"):
        port = config.port or 5432
        base_url = f"postgresql://{auth_part}{host}:{port}/{config.database}"
        if config.ssl_mode:
            base_url += f"?sslmode={config.ssl_mode}"
        return base_url

    elif db_type in ("mysql", "mariadb"):
        port = config.port or 3306
        return f"mysql+pymysql://{auth_part}{host}:{port}/{config.database}"

    elif db_type in ("mssql", "sqlserver"):
        port = config.port or 1433
        return f"mssql+pyodbc://{auth_part}{host}:{port}/{config.database}?driver=ODBC+Driver+17+for+SQL+Server"

    else:
        # Generic dialect fallback
        port_part = f":{config.port}" if config.port else ""
        return f"{db_type}://{auth_part}{host}{port_part}/{config.database}"


def test_connection(config: DatabaseConfig) -> Dict[str, Any]:
    """Test connecting to a database without persisting it to the registry.

    Returns connection health and basic server information.
    """
    url = build_connection_url(config)
    try:
        # Create a temporary engine with short timeout
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5} if "sqlite" not in url else {})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "success": True,
            "message": f"Successfully connected to {config.db_type} database '{config.database}'",
            "db_type": config.db_type,
            "database": config.database,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "db_type": config.db_type,
            "database": config.database,
        }


def reflect_schema_from_engine(engine: Engine) -> Dict[str, Any]:
    """Inspect and reflect full schema (tables, columns, types, PKs, FKs, sample values) from an engine."""
    inspector = inspect(engine)
    metadata: Dict[str, Any] = {}

    with engine.connect() as conn:
        for table_name in inspector.get_table_names():
            columns_dict = {}
            sample_values_dict = {}
            for col in inspector.get_columns(table_name):
                col_name = col["name"]
                col_type = str(col["type"])
                columns_dict[col_name] = col_type

                # Sample values for low-cardinality categorical text columns
                type_upper = col_type.upper()
                if any(t in type_upper for t in ("CHAR", "TEXT", "VARCHAR", "STRING")):
                    try:
                        sample_query = text(
                            f'SELECT DISTINCT "{col_name}" FROM "{table_name}" '
                            f'WHERE "{col_name}" IS NOT NULL LIMIT 11'
                        )
                        dist_vals = [row[0] for row in conn.execute(sample_query).fetchall() if row[0] is not None]
                        if 0 < len(dist_vals) <= 10:
                            sample_values_dict[col_name] = dist_vals[:8]
                    except Exception:
                        pass

            # Foreign keys
            foreign_keys = []
            try:
                fks = inspector.get_foreign_keys(table_name)
                for fk in fks:
                    referred_table = fk.get("referred_table")
                    constrained_cols = fk.get("constrained_columns", [])
                    referred_cols = fk.get("referred_columns", [])
                    if referred_table and constrained_cols:
                        foreign_keys.append({
                            "constrained_columns": constrained_cols,
                            "referred_table": referred_table,
                            "referred_columns": referred_cols,
                        })
            except Exception:
                foreign_keys = []

            # Primary keys
            primary_keys = []
            try:
                pk_info = inspector.get_pk_constraint(table_name)
                primary_keys = pk_info.get("constrained_columns", [])
            except Exception:
                primary_keys = []

            # Row count
            try:
                count_res = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                row_count = int(count_res) if count_res is not None else 0
            except Exception:
                row_count = 0

            # Table comment
            table_comment = ""
            try:
                comment_info = inspector.get_table_comment(table_name)
                table_comment = comment_info.get("text", "") or ""
            except Exception:
                table_comment = ""

            metadata[table_name] = {
                "name": table_name,
                "columns": columns_dict,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "sample_values": sample_values_dict,
                "comment": table_comment,
                "row_count": row_count,
            }

    return metadata


def register_database(config: DatabaseConfig) -> Dict[str, Any]:
    """Register and reflect a database connection.

    Tests the connection, extracts all schema metadata, and stores it in the active registry.
    """
    url = build_connection_url(config)
    engine = create_engine(url, pool_pre_ping=True)

    # Verify connectivity
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # Reflect schema
    schema = reflect_schema_from_engine(engine)

    # Store in registry
    _ACTIVE_CONNECTIONS[config.connection_id] = {
        "engine": engine,
        "config": config,
        "schema": schema,
        "dialect": config.db_type.lower(),
    }

    return {
        "connection_id": config.connection_id,
        "db_type": config.db_type,
        "database": config.database,
        "table_count": len(schema),
        "tables": list(schema.keys()),
        "status": "connected",
    }


def get_connection(connection_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve an active registered connection by ID.

    If connection_id is None, returns the first registered connection or None.
    """
    if connection_id and connection_id in _ACTIVE_CONNECTIONS:
        return _ACTIVE_CONNECTIONS[connection_id]

    if not connection_id and _ACTIVE_CONNECTIONS:
        first_key = next(iter(_ACTIVE_CONNECTIONS))
        return _ACTIVE_CONNECTIONS[first_key]

    return None


def get_connection_engine(connection_id: Optional[str] = None) -> Engine:
    """Get the SQLAlchemy engine for a registered connection.

    Defaults to local SQLite company.db if not found.
    """
    conn = get_connection(connection_id)
    if conn:
        return conn["engine"]

    from db.connectors import get_engine_for_dialect
    return get_engine_for_dialect("sqlite")


def get_connection_schema(connection_id: Optional[str] = None) -> Dict[str, Any]:
    """Get reflected schema metadata for a registered connection.

    Defaults to local SQLite company.db schema if not found.
    """
    conn = get_connection(connection_id)
    if conn:
        return conn["schema"]

    from db.connectors import get_full_schema_metadata
    return get_full_schema_metadata()


def list_registered_connections() -> List[Dict[str, Any]]:
    """List all currently active database connections."""
    summary = []
    for c_id, data in _ACTIVE_CONNECTIONS.items():
        conf = data["config"]
        schema = data["schema"]
        summary.append({
            "connection_id": c_id,
            "db_type": conf.db_type,
            "database": conf.database,
            "host": conf.host,
            "table_count": len(schema),
            "tables": list(schema.keys()),
        })
    return summary


def delete_connection(connection_id: str) -> bool:
    """Remove a database connection from the registry."""
    if connection_id in _ACTIVE_CONNECTIONS:
        del _ACTIVE_CONNECTIONS[connection_id]
        return True
    return False
