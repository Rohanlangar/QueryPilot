"""Database connectors, schema reflection, table extraction, and query execution.

Provides:
- SQLAlchemy engine factory for multiple dialects
- Full schema reflection and caching
- sqlparse-based table name extraction
- PII masking on query outputs (emails, phones, etc.)
- LangGraph execution node (execute_query_node)
"""

import os
import re
from typing import Dict, Any, List, Optional
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Function
from sqlparse.tokens import Keyword, DML
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

from config import DEFAULT_ROW_LIMIT

# Default SQLite database path
DEFAULT_DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "company.db")

# Cache for reflected schema metadata
_schema_cache: Dict[str, Any] = {}
_cached_engine: Optional[Engine] = None


def get_engine_for_dialect(dialect: str = "sqlite", db_url: Optional[str] = None) -> Engine:
    """Return a SQLAlchemy engine for the requested dialect.

    Defaults to the local company.db SQLite database.
    """
    global _cached_engine
    if db_url:
        return create_engine(db_url)

    normalized = (dialect or "sqlite").lower()
    if normalized == "sqlite":
        # Check if database exists, if not seed it
        if not os.path.exists(DEFAULT_DB_FILE):
            from db.seed import seed_database
            seed_database(DEFAULT_DB_FILE)
        return create_engine(f"sqlite:///{DEFAULT_DB_FILE}")

    # Fallback to in-memory or throw for unconfigured external DBs
    raise ValueError(f"No connection URL provided for dialect: {dialect}")


def get_full_schema_metadata(engine: Optional[Engine] = None, force_refresh: bool = False) -> Dict[str, Any]:
    """Reflect all tables, columns, types, primary keys, foreign keys,
    categorical sample values, comments, and row counts from the database.

    Caches results in memory for high-performance table retrieval and schema context.
    """
    global _schema_cache
    if _schema_cache and not force_refresh:
        return _schema_cache

    if engine is None:
        engine = get_engine_for_dialect("sqlite")

    inspector = inspect(engine)
    metadata: Dict[str, Any] = {}

    with engine.connect() as conn:
        for table_name in inspector.get_table_names():
            # Columns and types
            columns_dict = {}
            sample_values_dict = {}
            for col in inspector.get_columns(table_name):
                col_name = col["name"]
                col_type = str(col["type"])
                columns_dict[col_name] = col_type

                # For TEXT/VARCHAR columns, sample distinct values if cardinality is small (<= 10)
                type_upper = col_type.upper()
                if any(t in type_upper for t in ("CHAR", "TEXT", "VARCHAR", "STRING")):
                    try:
                        sample_query = text(
                            f'SELECT DISTINCT "{col_name}" FROM "{table_name}" '
                            f'WHERE "{col_name}" IS NOT NULL LIMIT 11'
                        )
                        dist_vals = [row[0] for row in conn.execute(sample_query).fetchall() if row[0] is not None]
                        # If low cardinality (<= 10), record sample values for categorical understanding
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

    _schema_cache = metadata
    return _schema_cache


def set_schema_metadata(metadata: Dict[str, Any]) -> None:
    """Manually override or seed schema metadata (useful in tests)."""
    global _schema_cache
    _schema_cache = metadata


# ---------------------------------------------------------------------------
# Robust table extraction using sqlparse + regex fallback
# ---------------------------------------------------------------------------

_FALLBACK_TABLE_PATTERN = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([`\"\[]?[\w]+[`\"\]]?)",
    re.IGNORECASE,
)


def _is_subselect(parsed):
    if not parsed.is_group:
        return False
    for item in parsed.tokens:
        if item.ttype is DML and item.value.upper() == "SELECT":
            return True
    return False


def _extract_from_part(token_stream):
    for token in token_stream:
        if isinstance(token, IdentifierList):
            for identifier in token.get_identifiers():
                yield identifier.get_real_name() or identifier.get_name()
        elif isinstance(token, Identifier):
            yield token.get_real_name() or token.get_name()
        elif token.ttype is Keyword:
            yield token.value


def extract_table_names(sql: str) -> List[str]:
    """Extract table names referenced in a SQL query.

    Uses sqlparse AST inspection and regex fallback to handle CTEs, aliases, and subqueries.
    """
    if not sql or not sql.strip():
        return []

    tables: Set[str] = set()
    try:
        parsed_statements = sqlparse.parse(sql)
        for statement in parsed_statements:
            from_seen = False
            for token in statement.tokens:
                if _is_subselect(token):
                    # Recurse for subselects
                    for sub_table in extract_table_names(str(token)):
                        tables.add(sub_table)
                if token.is_group:
                    for sub_token in token.tokens:
                        if _is_subselect(sub_token):
                            for sub_table in extract_table_names(str(sub_token)):
                                tables.add(sub_table)

                if token.ttype is Keyword and token.value.upper() in ("FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN"):
                    from_seen = True
                    continue
                if from_seen:
                    if isinstance(token, IdentifierList):
                        for identifier in token.get_identifiers():
                            real_name = identifier.get_real_name()
                            if real_name:
                                tables.add(real_name)
                        from_seen = False
                    elif isinstance(token, Identifier):
                        real_name = token.get_real_name()
                        if real_name:
                            tables.add(real_name)
                        from_seen = False
                    elif token.ttype is Keyword:
                        from_seen = False
    except Exception:
        pass

    # Extract Common Table Expressions (CTEs) defined in WITH clauses
    cte_pattern = re.compile(
        r"\b(?:WITH\s+(?:RECURSIVE\s+)?|,)\s*([`\"\[]?[\w]+[`\"\]]?)\s+AS\s*\(",
        re.IGNORECASE,
    )
    cte_matches = cte_pattern.findall(sql)
    cte_names = {c.strip("`\"[]").lower() for c in cte_matches}

    # Regex fallback to ensure no tables were missed
    matches = _FALLBACK_TABLE_PATTERN.findall(sql)
    for m in matches:
        cleaned = m.strip("`\"[]").strip()
        # Exclude SQL keywords mistakenly captured
        if cleaned.upper() not in ("SELECT", "WHERE", "GROUP", "ORDER", "LIMIT", "HAVING", "SET", "VALUES"):
            tables.add(cleaned)

    # Exclude CTE aliases so they are not mistaken for physical tables
    physical_tables = [t for t in tables if t.lower() not in cte_names]

    return sorted(physical_tables)


# ---------------------------------------------------------------------------
# PII Masking
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
_PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,4}[-.\s]*)?(?:\(?\d{2,4}\)?[-.\s]*)?\d{3,4}[-.\s]+\d{4}\b"
)


def _mask_email_match(match: re.Match) -> str:
    user, domain = match.group(1), match.group(2)
    if len(user) <= 2:
        return f"*@{domain}"
    return f"{user[0]}***{user[-1]}@{domain}"


def _mask_phone_match(match: re.Match) -> str:
    return "[REDACTED_PHONE]"


def mask_pii_value(val: Any) -> Any:
    """Mask sensitive string content like email addresses and phone numbers."""
    if not isinstance(val, str):
        return val

    masked = _EMAIL_PATTERN.sub(_mask_email_match, val)
    masked = _PHONE_PATTERN.sub(_mask_phone_match, masked)
    return masked


def mask_pii_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply PII masking across all returned rows and columns."""
    masked_rows = []
    for row in rows:
        masked_row = {}
        for col, val in row.items():
            col_lower = col.lower()
            if any(s in col_lower for s in ("password", "secret", "ssn", "token")):
                masked_row[col] = "[REDACTED]"
            elif any(s in col_lower for s in ("phone", "mobile", "tel")):
                masked_row[col] = "[REDACTED_PHONE]"
            else:
                masked_row[col] = mask_pii_value(val)
        masked_rows.append(masked_row)
    return masked_rows


# ---------------------------------------------------------------------------
# LangGraph Query Execution Node
# ---------------------------------------------------------------------------

def execute_query_node(state: dict) -> dict:
    """Execute read-only queries against their respective target database engines.

    Supports both single database and multi-database execution.
    Applies row capping and PII masking on each returned dataset.
    """
    import logging
    logger = logging.getLogger("querypilot.federation")

    from db.connection_manager import get_connection_engine

    database_queries = state.get("database_queries", {})
    fallback_sql = state.get("optimized_sql") or state.get("generated_sql")

    if not database_queries and fallback_sql:
        target_db = state.get("connection_id") or "default"
        database_queries = {target_db: fallback_sql}

    if not database_queries:
        return {
            "database_results": {},
            "query_result": [],
            "row_count": 0,
            "execution_error": "No SQL query provided for execution.",
            "error": "No SQL query provided for execution.",
        }

    database_results: Dict[str, Any] = {}
    primary_results = []
    primary_row_count = 0

    try:
        for db_id, sql in database_queries.items():
            if not sql or not sql.strip():
                continue

            engine = get_connection_engine(db_id if db_id != "default" else state.get("connection_id"))
            with engine.connect() as conn:
                result_proxy = conn.execute(text(sql))
                if result_proxy.returns_rows:
                    keys = list(result_proxy.keys())
                    raw_rows = []
                    for row in result_proxy.fetchmany(DEFAULT_ROW_LIMIT):
                        row_dict = {}
                        for k, v in zip(keys, row):
                            if hasattr(v, "isoformat"):
                                row_dict[k] = v.isoformat()
                            elif isinstance(v, (bytes, bytearray)):
                                row_dict[k] = v.hex()
                            else:
                                row_dict[k] = v
                        raw_rows.append(row_dict)
                    masked_rows = mask_pii_rows(raw_rows)
                    database_results[db_id] = {
                        "columns": keys,
                        "rows": masked_rows,
                        "row_count": len(masked_rows),
                    }
                    logger.info(f"[EXECUTION] Database '{db_id}': Success ({len(masked_rows)} rows returned)")
                    if not primary_results:
                        primary_results = masked_rows
                        primary_row_count = len(masked_rows)
                else:
                    database_results[db_id] = {
                        "columns": ["status", "rows_affected"],
                        "rows": [{"status": "Success", "rows_affected": result_proxy.rowcount}],
                        "row_count": result_proxy.rowcount,
                    }
                    logger.info(f"[EXECUTION] Database '{db_id}': Statement executed ({result_proxy.rowcount} rows affected)")

        return {
            "database_results": database_results,
            "query_result": primary_results,
            "row_count": primary_row_count,
            "execution_error": None,
            "error": None,
        }

    except Exception as e:
        err_msg = str(e)
        logger.error(f"[EXECUTION] Error during execution: {err_msg}")
        return {
            "database_results": database_results,
            "query_result": [],
            "row_count": 0,
            "execution_error": err_msg,
            "error": f"Database execution error: {err_msg}",
        }
