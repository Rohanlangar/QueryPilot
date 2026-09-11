"""
RBAC models — Role-Based Access Control.

Defines roles and per-table access policies that control which
database tables and columns a user can query.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Role(Base):
    """
    User roles with hierarchical permissions.

    Built-in roles:
      - admin: Full access, can manage users and policies
      - analyst: Can query all non-restricted tables
      - viewer: Read-only, limited to approved tables only
    """

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    can_manage_users: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_connections: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_policies: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_audit: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    table_policies = relationship("TablePolicy", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class TablePolicy(Base):
    """
    Per-table access policy scoped to a role and database connection.

    Controls:
      - Whether a role can query a specific table at all
      - Which columns within that table are marked as sensitive/blocked
    """

    __tablename__ = "table_policies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sensitive_columns: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON array of column names to mask
    blocked_columns: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON array of columns completely hidden
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    role = relationship("Role", back_populates="table_policies")
    connection = relationship("Connection", back_populates="table_policies")

    def __repr__(self) -> str:
        status = "allowed" if self.allowed else "blocked"
        return f"<TablePolicy {self.table_name} ({status}) for role={self.role_id[:8]}...>"
