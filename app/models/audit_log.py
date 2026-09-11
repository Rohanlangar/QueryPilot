"""
AuditLog model — full query provenance trail.

Every query and significant action is logged immutably for
compliance (SOC2, HIPAA, GDPR) and admin visibility.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    connection_id: Mapped[str] = mapped_column(
        String(36), nullable=True, index=True
    )

    # ── Action Details ────────────────────────────────────────
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "query", "login", "connection_created", "schema_sync", "export", etc.
    natural_language_input: Mapped[str] = mapped_column(Text, nullable=True)
    sql_generated: Mapped[str] = mapped_column(Text, nullable=True)
    sql_executed: Mapped[str] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str] = mapped_column(Text, nullable=True)  # Brief summary, not full data
    rows_returned: Mapped[int] = mapped_column(Integer, nullable=True)

    # ── Pipeline Metadata ─────────────────────────────────────
    confidence_score: Mapped[float] = mapped_column(nullable=True)
    validation_passed: Mapped[bool] = mapped_column(nullable=True)
    was_cached: Mapped[bool] = mapped_column(default=False)
    execution_time_ms: Mapped[float] = mapped_column(nullable=True)

    # ── Request Metadata ──────────────────────────────────────
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)

    # ── Error Info ────────────────────────────────────────────
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="success", nullable=False
    )  # "success", "error", "blocked"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by user={self.user_id} at {self.created_at}>"
