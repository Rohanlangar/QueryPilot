# agent/schema_agent.py
"""Schema Discovery Agent — Graph Node.

Retrieves and catalogs schema metadata across ALL active connected databases.
Builds a unified logical representation of available schemas including
table names, column types, primary keys, foreign keys, and cross-database
key correlations.
"""

import logging
from typing import Dict, Any

from db.connection_manager import (
    get_unified_schema_metadata,
    detect_cross_database_relationships,
    get_connection,
)

logger = logging.getLogger("querypilot.federation")


def schema_node(state: dict) -> dict:
    """LangGraph node: discover and catalog schemas across all active databases.

    Reads:
        state["question"]
        state.get("active_connections")
        state.get("connection_id")

    Returns partial state update:
        {
            "unified_schema": {db_id: db_meta, ...},
            "cross_db_relationships": [...],
            "db_dialect": str,
            "relevant_schema": {table_name: table_meta, ...},
        }
    """
    active_ids = state.get("active_connections")
    conn_id = state.get("connection_id")

    # If single connection_id is explicitly targeted and no active_connections list
    if conn_id and not active_ids:
        active_ids = [conn_id]

    # Discover unified schema across all active connections
    unified_schema = get_unified_schema_metadata(active_ids)
    cross_db_rels = detect_cross_database_relationships(unified_schema)

    # Flatten all tables for backward compatibility
    flattened_tables = {}
    for db_id, db_data in unified_schema.items():
        for t_name, t_meta in db_data.get("tables", {}).items():
            key = t_name if t_name not in flattened_tables else f"{db_id}.{t_name}"
            flattened_tables[key] = t_meta

    # Determine primary dialect
    primary_dialect = "sqlite"
    for db_data in unified_schema.values():
        dialect = db_data.get("dialect", "").lower()
        if "postgres" in dialect:
            primary_dialect = "postgresql"
            break
        elif dialect:
            primary_dialect = dialect

    logger.info(
        f"[SCHEMA DISCOVERY] Discovered {len(unified_schema)} database(s) with {len(flattened_tables)} total table(s). "
        f"Cross-DB joins detected: {len(cross_db_rels)}"
    )

    return {
        "unified_schema": unified_schema,
        "cross_db_relationships": cross_db_rels,
        "db_dialect": primary_dialect,
        "relevant_schema": flattened_tables,
    }
