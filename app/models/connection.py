"""
Connection model — saved external database connections.

Credentials are encrypted at rest using Fernet symmetric encryption.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    db_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # postgresql, mysql, mssql, oracle
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    ssl_enabled: Mapped[bool] = mapped_column(default=False)
    extra_params: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON string for additional connection params
    is_active: Mapped[bool] = mapped_column(default=True)
    last_tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner = relationship("User", back_populates="connections")
    chat_sessions = relationship("ChatSession", back_populates="connection", cascade="all, delete-orphan")
    schema_metadata = relationship("SchemaMetadata", back_populates="connection", cascade="all, delete-orphan")
    table_policies = relationship("TablePolicy", back_populates="connection", cascade="all, delete-orphan")
    cache_entries = relationship("CacheEntry", back_populates="connection", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Connection {self.name} ({self.db_type}://{self.host}:{self.port}/{self.database_name})>"
