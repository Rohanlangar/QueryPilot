"""
QueryPilot — Schema Introspector

Connects to external databases and extracts full schema metadata:
tables, columns, types, keys, indexes, and approximate row counts.
Stores results in SchemaMetadata for fast retrieval.
"""

import time
import logging
from typing import List, Dict, Optional

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.schema_metadata import SchemaMetadata

logger = logging.getLogger(__name__)


class SchemaIntrospector:
    """
    Extracts and caches database schema metadata from external connections.
    """

    async def sync_schema(
        self,
        engine: AsyncEngine,
        connection_id: str,
        db: AsyncSession,
    ) -> dict:
        """
        Full schema sync — introspects the database and stores metadata.

        Returns: {tables_found: int, columns_found: int, sync_duration_ms: float, errors: []}
        """
        start = time.perf_counter()
        errors = []
        tables_found = 0
        columns_found = 0

        try:
            # Delete existing metadata for this connection
            await db.execute(
                delete(SchemaMetadata).where(SchemaMetadata.connection_id == connection_id)
            )

            # Run introspection in a sync context (SQLAlchemy inspect requires it)
            async with engine.connect() as conn:
                def _introspect(sync_conn):
                    """Synchronous introspection using SQLAlchemy inspector."""
                    insp = inspect(sync_conn)
                    schema_data = []

                    # Get default schema
                    default_schema = insp.default_schema_name or "public"

                    for table_name in insp.get_table_names(schema=default_schema):
                        try:
                            columns = insp.get_columns(table_name, schema=default_schema)
                            pk_constraint = insp.get_pk_constraint(table_name, schema=default_schema)
                            pk_columns = set(pk_constraint.get("constrained_columns", []))
                            fk_list = insp.get_foreign_keys(table_name, schema=default_schema)
                            indexes = insp.get_indexes(table_name, schema=default_schema)

                            # Build FK lookup: column → (ref_table, ref_column)
                            fk_map = {}
                            for fk in fk_list:
                                for i, col in enumerate(fk.get("constrained_columns", [])):
                                    ref_cols = fk.get("referred_columns", [])
                                    fk_map[col] = (
                                        fk.get("referred_table", ""),
                                        ref_cols[i] if i < len(ref_cols) else "",
                                    )

                            # Build index lookup
                            indexed_cols = set()
                            unique_cols = set()
                            for idx in indexes:
                                for col in idx.get("column_names", []):
                                    if col:
                                        indexed_cols.add(col)
                                        if idx.get("unique"):
                                            unique_cols.add(col)

                            for pos, col_info in enumerate(columns, 1):
                                col_name = col_info["name"]
                                fk_ref = fk_map.get(col_name)

                                schema_data.append({
                                    "table_schema": default_schema,
                                    "table_name": table_name,
                                    "column_name": col_name,
                                    "data_type": str(col_info.get("type", "UNKNOWN")),
                                    "is_nullable": col_info.get("nullable", True),
                                    "column_default": str(col_info.get("default")) if col_info.get("default") else None,
                                    "ordinal_position": pos,
                                    "is_primary_key": col_name in pk_columns,
                                    "is_foreign_key": col_name in fk_map,
                                    "fk_references_table": fk_ref[0] if fk_ref else None,
                                    "fk_references_column": fk_ref[1] if fk_ref else None,
                                    "is_indexed": col_name in indexed_cols,
                                    "is_unique": col_name in unique_cols,
                                })
                        except Exception as e:
                            errors.append(f"Error introspecting table '{table_name}': {str(e)}")
                            logger.warning(f"Error introspecting {table_name}: {e}")

                    return schema_data

                schema_data = await conn.run_sync(_introspect)

            # Collect unique table names
            table_names = {row_data["table_name"] for row_data in schema_data}
            tables_found = len(table_names)

            # Attempt to get row counts for each table
            table_counts = {}
            async with engine.connect() as conn:
                for table_name in table_names:
                    try:
                        result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                        table_counts[table_name] = result.scalar()
                    except Exception as e:
                        logger.debug(f"Could not count rows for '{table_name}': {e}")
                        table_counts[table_name] = None

            # Store metadata rows
            for row_data in schema_data:
                table_name = row_data["table_name"]
                metadata_row = SchemaMetadata(
                    connection_id=connection_id,
                    table_row_count=table_counts.get(table_name),
                    **row_data,
                )
                db.add(metadata_row)
                columns_found += 1

            await db.flush()

        except Exception as e:
            errors.append(f"Schema sync failed: {str(e)}")
            logger.error(f"Schema sync failed for connection {connection_id}: {e}")

        duration = (time.perf_counter() - start) * 1000
        logger.info(
            f"Schema sync for {connection_id}: {tables_found} tables, "
            f"{columns_found} columns in {duration:.0f}ms"
        )

        return {
            "connection_id": connection_id,
            "tables_found": tables_found,
            "columns_found": columns_found,
            "sync_duration_ms": round(duration, 2),
            "errors": errors,
        }

    async def get_tables(
        self, connection_id: str, db: AsyncSession
    ) -> List[dict]:
        """Get list of tables with column counts and row counts."""
        from sqlalchemy import func

        stmt = (
            select(
                SchemaMetadata.table_schema,
                SchemaMetadata.table_name,
                SchemaMetadata.table_description,
                SchemaMetadata.table_row_count,
                func.count(SchemaMetadata.id).label("column_count"),
            )
            .where(SchemaMetadata.connection_id == connection_id)
            .group_by(
                SchemaMetadata.table_schema,
                SchemaMetadata.table_name,
                SchemaMetadata.table_description,
                SchemaMetadata.table_row_count,
            )
            .order_by(SchemaMetadata.table_name)
        )
        result = await db.execute(stmt)
        rows = result.all()

        return [
            {
                "table_schema": r.table_schema,
                "table_name": r.table_name,
                "table_description": r.table_description,
                "row_count": r.table_row_count,
                "column_count": r.column_count,
            }
            for r in rows
        ]

    async def get_columns(
        self, connection_id: str, table_name: str, db: AsyncSession
    ) -> List[SchemaMetadata]:
        """Get all columns for a specific table."""
        stmt = (
            select(SchemaMetadata)
            .where(
                SchemaMetadata.connection_id == connection_id,
                SchemaMetadata.table_name == table_name,
            )
            .order_by(SchemaMetadata.ordinal_position)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_schema_context(
        self,
        connection_id: str,
        table_names: Optional[List[str]],
        db: AsyncSession,
    ) -> Dict:
        """
        Build a compressed schema context for the SQL generation agent.

        Returns a dict like:
        {
            "tables": {
                "orders": {
                    "columns": [{"name": "id", "type": "INTEGER", "pk": true}, ...],
                    "foreign_keys": [{"column": "user_id", "references": "users.id"}],
                    "row_count": 50000,
                }
            }
        }
        """
        stmt = select(SchemaMetadata).where(
            SchemaMetadata.connection_id == connection_id
        )
        if table_names:
            stmt = stmt.where(SchemaMetadata.table_name.in_(table_names))

        result = await db.execute(stmt)
        rows = result.scalars().all()

        tables = {}
        for row in rows:
            if row.table_name not in tables:
                tables[row.table_name] = {
                    "schema": row.table_schema,
                    "description": row.table_description,
                    "row_count": row.table_row_count,
                    "columns": [],
                    "foreign_keys": [],
                }

            col_info = {
                "name": row.column_name,
                "type": row.data_type,
                "nullable": row.is_nullable,
                "pk": row.is_primary_key,
                "indexed": row.is_indexed,
            }
            if row.column_description:
                col_info["description"] = row.column_description
            tables[row.table_name]["columns"].append(col_info)

            if row.is_foreign_key:
                tables[row.table_name]["foreign_keys"].append({
                    "column": row.column_name,
                    "references": f"{row.fk_references_table}.{row.fk_references_column}",
                })

        return {"tables": tables}


# Singleton instance
schema_introspector = SchemaIntrospector()
