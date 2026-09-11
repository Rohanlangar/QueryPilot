"""
Schema introspection schemas — request/response models for schema endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class TableInfo(BaseModel):
    """Summary info about a database table."""
    table_schema: str
    table_name: str
    table_description: Optional[str] = None
    row_count: Optional[int] = None
    column_count: int


class ColumnInfo(BaseModel):
    """Detailed column metadata."""
    column_name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    fk_references_table: Optional[str] = None
    fk_references_column: Optional[str] = None
    is_indexed: bool = False
    is_unique: bool = False
    is_pii: bool = False
    pii_type: Optional[str] = None
    column_description: Optional[str] = None
    ordinal_position: Optional[int] = None

    model_config = {"from_attributes": True}


class TableDetail(BaseModel):
    """Full table metadata with columns."""
    table_schema: str
    table_name: str
    table_description: Optional[str] = None
    row_count: Optional[int] = None
    columns: List[ColumnInfo] = []


class SchemaOverview(BaseModel):
    """Full schema overview for a connection."""
    connection_id: str
    database_name: str
    tables: List[TableInfo]
    total_tables: int
    last_synced_at: Optional[datetime] = None


class ColumnUpdate(BaseModel):
    """Update column metadata (description, PII tag)."""
    column_description: Optional[str] = None
    is_pii: Optional[bool] = None
    pii_type: Optional[str] = None


class SchemaSyncResult(BaseModel):
    """Result of a schema sync operation."""
    connection_id: str
    tables_found: int
    columns_found: int
    sync_duration_ms: float
    errors: List[str] = []
