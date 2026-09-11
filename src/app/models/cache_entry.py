"""
CacheEntry model — semantic query caching.

Stores previously generated SQL and results keyed by a normalized
hash of the natural-language question, scoped per database connection.
Expired entries are cleaned up by TTL.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    connection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # SHA-256 of normalized question
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    sql_generated: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=True)
    result_row_count: Mapped[int] = mapped_column(nullable=True)

    # ── TTL ───────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # ── Hit Tracking ──────────────────────────────────────────
    hit_count: Mapped[int] = mapped_column(default=0)
    last_hit_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    connection = relationship("Connection", back_populates="cache_entries")

    def __repr__(self) -> str:
        return f"<CacheEntry hash={self.question_hash[:12]}... hits={self.hit_count}>"
