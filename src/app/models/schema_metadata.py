"""
SchemaMetadata model — cached introspection data from external databases.

Stores per-column metadata (types, keys, descriptions, PII tags) to
avoid repeated introspection calls and to enable fast schema context
retrieval for the SQL generation agent.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class SchemaMetadata(Base):
    __tablename__ = "schema_metadata"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    connection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("connections.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Table Info ────────────────────────────────────────────
    table_schema: Mapped[str] = mapped_column(
        String(255), default="public", nullable=False
    )  # Schema/namespace (e.g., "public", "dbo")
    table_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    table_description: Mapped[str] = mapped_column(Text, nullable=True)  # User-provided or auto-inferred
    table_row_count: Mapped[int] = mapped_column(BigInteger, nullable=True)

    # ── Column Info ───────────────────────────────────────────
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    column_description: Mapped[str] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, default=True)
    column_default: Mapped[str] = mapped_column(String(500), nullable=True)
    ordinal_position: Mapped[int] = mapped_column(Integer, nullable=True)

    # ── Key Info ──────────────────────────────────────────────
    is_primary_key: Mapped[bool] = mapped_column(Boolean, default=False)
    is_foreign_key: Mapped[bool] = mapped_column(Boolean, default=False)
    fk_references_table: Mapped[str] = mapped_column(String(255), nullable=True)
    fk_references_column: Mapped[str] = mapped_column(String(255), nullable=True)

    # ── Index Info ────────────────────────────────────────────
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unique: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── PII & Sensitivity Tagging ─────────────────────────────
    is_pii: Mapped[bool] = mapped_column(Boolean, default=False)
    pii_type: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # "email", "ssn", "phone", "name", "address", etc.

    # ── Metadata ──────────────────────────────────────────────
    sample_values: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON array of sample values (non-PII only)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    connection = relationship("Connection", back_populates="schema_metadata")

    def __repr__(self) -> str:
        return f"<SchemaMetadata {self.table_name}.{self.column_name} ({self.data_type})>"
