"""
ChatMessage model — individual messages within a conversation session.

Stores both user questions and system responses, including the
generated SQL, execution results, confidence scoring, and
visualization suggestions.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Natural language text

    # ── SQL & Results (populated for assistant messages) ──────
    sql_generated: Mapped[str] = mapped_column(Text, nullable=True)
    sql_executed: Mapped[str] = mapped_column(Text, nullable=True)  # May differ after optimization
    results_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON serialized results
    result_row_count: Mapped[int] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=True)

    # ── Confidence & Visualization ────────────────────────────
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0.0–1.0
    confidence_reason: Mapped[str] = mapped_column(Text, nullable=True)
    suggested_chart_type: Mapped[str] = mapped_column(String(50), nullable=True)
    chart_config_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON chart config

    # ── Suggested Follow-ups ──────────────────────────────────
    follow_up_suggestions_json: Mapped[str] = mapped_column(Text, nullable=True)

    # ── Error Tracking ────────────────────────────────────────
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatMessage {self.role}: '{preview}'>"
