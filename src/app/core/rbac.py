"""
QueryPilot — RBAC Engine

Role-Based Access Control for database table and column access.
Checks table policies to determine if a user can query specific tables
and identifies sensitive/blocked columns.
"""

import json
import logging
from typing import List, Set, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Role, TablePolicy
from app.models.user import User

logger = logging.getLogger(__name__)


class RBACEngine:
    """Evaluates access policies for users against database tables."""

    async def get_user_role(self, user: User, db: AsyncSession) -> Optional[Role]:
        """Fetch the Role object for a user."""
        result = await db.execute(select(Role).where(Role.name == user.role))
        return result.scalar_one_or_none()

    async def get_policies_for_role(
        self, role_name: str, connection_id: str, db: AsyncSession
    ) -> List[TablePolicy]:
        """Get all table policies for a role on a specific connection."""
        result = await db.execute(
            select(TablePolicy)
            .join(Role)
            .where(
                Role.name == role_name,
                TablePolicy.connection_id == connection_id,
            )
        )
        return result.scalars().all()

    async def check_table_access(
        self,
        user: User,
        connection_id: str,
        table_names: List[str],
        db: AsyncSession,
    ) -> dict:
        """
        Check if a user can access the given tables.

        Returns:
            {
                "allowed": bool,
                "blocked_tables": ["table1", "table2"],
                "reason": "..."
            }
        """
        # Admin has full access
        if user.role == "admin":
            return {"allowed": True, "blocked_tables": [], "reason": "Admin access"}

        policies = await self.get_policies_for_role(user.role, connection_id, db)

        # Build policy lookup
        policy_map: Dict[str, TablePolicy] = {p.table_name: p for p in policies}

        blocked = []
        for table in table_names:
            policy = policy_map.get(table)
            if policy and not policy.allowed:
                blocked.append(table)

        if blocked:
            return {
                "allowed": False,
                "blocked_tables": blocked,
                "reason": f"Access denied to tables: {', '.join(blocked)}",
            }

        return {"allowed": True, "blocked_tables": [], "reason": "Access granted"}

    async def get_sensitive_columns(
        self,
        user: User,
        connection_id: str,
        table_name: str,
        db: AsyncSession,
    ) -> Dict[str, List[str]]:
        """
        Get columns that should be masked or blocked for a user's role.

        Returns:
            {
                "sensitive": ["email", "phone"],  # Mask these
                "blocked": ["ssn", "salary"],     # Hide these entirely
            }
        """
        if user.role == "admin":
            return {"sensitive": [], "blocked": []}

        policies = await self.get_policies_for_role(user.role, connection_id, db)
        policy = next((p for p in policies if p.table_name == table_name), None)

        sensitive = []
        blocked = []

        if policy:
            if policy.sensitive_columns:
                try:
                    sensitive = json.loads(policy.sensitive_columns)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid sensitive_columns JSON for policy {policy.id}")

            if policy.blocked_columns:
                try:
                    blocked = json.loads(policy.blocked_columns)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid blocked_columns JSON for policy {policy.id}")

        return {"sensitive": sensitive, "blocked": blocked}

    async def get_all_blocked_tables(
        self,
        user: User,
        connection_id: str,
        db: AsyncSession,
    ) -> Set[str]:
        """Get all tables blocked for a user on a connection."""
        if user.role == "admin":
            return set()

        policies = await self.get_policies_for_role(user.role, connection_id, db)
        return {p.table_name for p in policies if not p.allowed}


# Singleton instance
rbac_engine = RBACEngine()
