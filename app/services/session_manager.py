"""
QueryPilot — Session Manager

Manages multi-turn chat sessions: creation, context retrieval,
and message history management. The context window (last N messages)
is what gets passed to agents for follow-up handling.
"""

import logging
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import ChatSession
from app.models.message import ChatMessage

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages multi-turn conversation state."""

    async def create_session(
        self,
        user_id: str,
        connection_id: str,
        title: str = "New Conversation",
        db: AsyncSession = None,
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            user_id=user_id,
            connection_id=connection_id,
            title=title,
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
        logger.info(f"Created session {session.id[:8]}... for user {user_id[:8]}...")
        return session

    async def get_session(
        self, session_id: str, db: AsyncSession
    ) -> Optional[ChatSession]:
        """Get a session by ID with all messages loaded."""
        result = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self, user_id: str, db: AsyncSession
    ) -> List[dict]:
        """Get all sessions for a user with message counts."""
        # Subquery for message count
        msg_count = (
            select(func.count(ChatMessage.id))
            .where(ChatMessage.session_id == ChatSession.id)
            .correlate(ChatSession)
            .scalar_subquery()
        )

        result = await db.execute(
            select(
                ChatSession,
                msg_count.label("message_count"),
            )
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        rows = result.all()

        return [
            {
                "id": row.ChatSession.id,
                "connection_id": row.ChatSession.connection_id,
                "title": row.ChatSession.title,
                "summary": row.ChatSession.summary,
                "is_active": row.ChatSession.is_active,
                "created_at": row.ChatSession.created_at,
                "updated_at": row.ChatSession.updated_at,
                "message_count": row.message_count,
            }
            for row in rows
        ]

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        db: AsyncSession,
        sql_generated: str = None,
        sql_executed: str = None,
        results_json: str = None,
        result_row_count: int = None,
        execution_time_ms: float = None,
        confidence_score: float = None,
        confidence_reason: str = None,
        suggested_chart_type: str = None,
        chart_config_json: str = None,
        follow_up_suggestions_json: str = None,
        error_message: str = None,
    ) -> ChatMessage:
        """Add a message to a session."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sql_generated=sql_generated,
            sql_executed=sql_executed,
            results_json=results_json,
            result_row_count=result_row_count,
            execution_time_ms=execution_time_ms,
            confidence_score=confidence_score,
            confidence_reason=confidence_reason,
            suggested_chart_type=suggested_chart_type,
            chart_config_json=chart_config_json,
            follow_up_suggestions_json=follow_up_suggestions_json,
            error_message=error_message,
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message

    async def get_context(
        self,
        session_id: str,
        db: AsyncSession,
        last_n: int = 5,
    ) -> List[ChatMessage]:
        """
        Get the last N messages from a session for context.

        This is what gets passed to the SQL generation agent so it can
        handle follow-up questions like 'now filter that to last quarter'.
        """
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(last_n)
        )
        messages = result.scalars().all()
        # Return in chronological order
        return list(reversed(messages))

    async def update_session_title(
        self, session_id: str, title: str, db: AsyncSession
    ):
        """Update a session's title."""
        session = await self.get_session(session_id, db)
        if session:
            session.title = title
            await db.flush()

    async def delete_session(self, session_id: str, db: AsyncSession) -> bool:
        """Delete a session and all its messages."""
        session = await self.get_session(session_id, db)
        if session:
            await db.delete(session)
            await db.flush()
            return True
        return False


# Singleton instance
session_manager = SessionManager()
