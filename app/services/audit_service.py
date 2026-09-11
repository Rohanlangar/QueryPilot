"""
QueryPilot — Audit Service

Immutable, append-only logging of all queries and significant actions
for enterprise compliance (SOC2, HIPAA, GDPR).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Append-only audit trail for query provenance and compliance."""

    async def log_query(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str = None,
        connection_id: str = None,
        natural_language_input: str = None,
        sql_generated: str = None,
        sql_executed: str = None,
        result_summary: str = None,
        rows_returned: int = None,
        confidence_score: float = None,
        validation_passed: bool = None,
        was_cached: bool = False,
        execution_time_ms: float = None,
        ip_address: str = None,
        user_agent: str = None,
        error_message: str = None,
        status: str = "success",
    ) -> AuditLog:
        """Log a query action."""
        log_entry = AuditLog(
            user_id=user_id,
            session_id=session_id,
            connection_id=connection_id,
            action="query",
            natural_language_input=natural_language_input,
            sql_generated=sql_generated,
            sql_executed=sql_executed,
            result_summary=result_summary,
            rows_returned=rows_returned,
            confidence_score=confidence_score,
            validation_passed=validation_passed,
            was_cached=was_cached,
            execution_time_ms=execution_time_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
            status=status,
        )
        db.add(log_entry)
        await db.flush()
        return log_entry

    async def log_action(
        self,
        db: AsyncSession,
        user_id: str,
        action: str,
        ip_address: str = None,
        user_agent: str = None,
        status: str = "success",
        error_message: str = None,
        **kwargs,
    ) -> AuditLog:
        """Log a non-query action (login, connection created, etc.)."""
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            **{k: v for k, v in kwargs.items() if hasattr(AuditLog, k)},
        )
        db.add(log_entry)
        await db.flush()
        return log_entry

    async def get_logs(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Get paginated audit logs with optional filters."""
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        # Apply filters
        filters = []
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if session_id:
            filters.append(AuditLog.session_id == session_id)
        if connection_id:
            filters.append(AuditLog.connection_id == connection_id)
        if action:
            filters.append(AuditLog.action == action)
        if status:
            filters.append(AuditLog.status == status)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = (
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(query)
        logs = result.scalars().all()

        total_pages = (total + page_size - 1) // page_size

        return {
            "logs": logs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_stats(self, db: AsyncSession) -> dict:
        """Get aggregate audit statistics for admin dashboard."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())

        # Total queries
        total_result = await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.action == "query")
        )
        total_queries = total_result.scalar() or 0

        # Queries today
        today_result = await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.action == "query",
                AuditLog.created_at >= today_start,
            )
        )
        queries_today = today_result.scalar() or 0

        # Queries this week
        week_result = await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.action == "query",
                AuditLog.created_at >= week_start,
            )
        )
        queries_this_week = week_result.scalar() or 0

        # Average execution time
        avg_result = await db.execute(
            select(func.avg(AuditLog.execution_time_ms)).where(
                AuditLog.action == "query",
                AuditLog.execution_time_ms.isnot(None),
            )
        )
        avg_execution_time = avg_result.scalar()

        # Cache hit rate
        cached_result = await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.action == "query",
                AuditLog.was_cached == True,
            )
        )
        cached_count = cached_result.scalar() or 0
        cache_hit_rate = (cached_count / total_queries * 100) if total_queries > 0 else 0

        # Error rate
        error_result = await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.action == "query",
                AuditLog.status == "error",
            )
        )
        error_count = error_result.scalar() or 0
        error_rate = (error_count / total_queries * 100) if total_queries > 0 else 0

        return {
            "total_queries": total_queries,
            "queries_today": queries_today,
            "queries_this_week": queries_this_week,
            "avg_execution_time_ms": round(avg_execution_time, 2) if avg_execution_time else None,
            "cache_hit_rate": round(cache_hit_rate, 2),
            "error_rate": round(error_rate, 2),
            "top_users": [],  # TODO: populate with top querying users
            "top_tables": [],  # TODO: populate from audit logs
        }


# Singleton instance
audit_service = AuditService()
