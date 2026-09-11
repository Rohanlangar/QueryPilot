"""
QueryPilot — Chat Routes

Core chat endpoints: sessions, messages, and the main query pipeline.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.connection import Connection
from app.models.user import User
from app.core.security import get_current_user
from app.core.json_utils import safe_json_dumps
from app.services.session_manager import session_manager
from app.services.semantic_cache import semantic_cache
from app.services.audit_service import audit_service
from app.services.pipeline import agent_pipeline
from app.services.connection_manager import connection_manager
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionDetailResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    QueryResponse,
    ExplainSQLRequest,
    ExplainSQLResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: ChatSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session tied to a database connection."""
    # Verify connection exists and belongs to user
    result = await db.execute(
        select(Connection).where(
            Connection.id == body.connection_id,
            Connection.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Connection not found")

    session = await session_manager.create_session(
        user_id=user.id,
        connection_id=body.connection_id,
        title=body.title or "New Conversation",
        db=db,
    )

    return ChatSessionResponse(
        id=session.id,
        connection_id=session.connection_id,
        title=session.title,
        summary=session.summary,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's chat sessions."""
    sessions = await session_manager.get_user_sessions(user.id, db)
    return [ChatSessionResponse(**s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a session with all its messages."""
    session = await session_manager.get_session(session_id, db)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    return ChatSessionDetailResponse(
        id=session.id,
        connection_id=session.connection_id,
        title=session.title,
        summary=session.summary,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[ChatMessageResponse.model_validate(m) for m in session.messages],
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    session = await session_manager.get_session(session_id, db)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_manager.delete_session(session_id, db)


@router.post("/sessions/{session_id}/messages", response_model=QueryResponse)
async def send_message(
    session_id: str,
    body: ChatMessageCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message (question) and receive the full pipeline response.

    This is the main endpoint — it:
    1. Saves the user message
    2. Checks semantic cache
    3. Runs the 5-agent pipeline (if not cached)
    4. Saves the assistant response
    5. Logs to audit trail
    6. Returns the full response with explanation, SQL, results, and viz suggestion
    """
    # Verify session ownership
    session = await session_manager.get_session(session_id, db)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get connection info
    result = await db.execute(
        select(Connection).where(Connection.id == session.connection_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Save user message
    await session_manager.add_message(
        session_id=session_id,
        role="user",
        content=body.content,
        db=db,
    )

    # Check semantic cache first
    cached = await semantic_cache.check_cache(body.content, conn.id, db)
    was_cached = cached is not None

    if cached:
        # Serve from cache
        results_data = json.loads(cached.result_json) if cached.result_json else None
        assistant_msg = await session_manager.add_message(
            session_id=session_id,
            role="assistant",
            content="(Cached result)",
            sql_generated=cached.sql_generated,
            sql_executed=cached.sql_generated,
            results_json=cached.result_json,
            result_row_count=cached.result_row_count,
            db=db,
        )

        # Log to audit
        await audit_service.log_query(
            db=db,
            user_id=user.id,
            session_id=session_id,
            connection_id=conn.id,
            natural_language_input=body.content,
            sql_generated=cached.sql_generated,
            sql_executed=cached.sql_generated,
            rows_returned=cached.result_row_count,
            was_cached=True,
            ip_address=request.client.host if request.client else None,
            status="success",
        )

        return QueryResponse(
            message=ChatMessageResponse.model_validate(assistant_msg),
            explanation="(Served from cache — this query was previously answered)",
            sql=cached.sql_generated,
            results=results_data.get("rows") if results_data else None,
            columns=results_data.get("columns") if results_data else None,
            row_count=cached.result_row_count,
            was_cached=True,
        )

    # Build conversation history for context
    context_messages = await session_manager.get_context(session_id, db, last_n=5)
    conversation_history = [
        {"role": m.role, "content": m.content, "sql": m.sql_generated}
        for m in context_messages
    ]

    # Ensure engine is ready
    try:
        await connection_manager.create_engine(conn)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to database: {str(e)}",
        )

    # Run the agent pipeline
    pipeline_result = await agent_pipeline.run(
        query=body.content,
        connection_id=conn.id,
        db_type=conn.db_type,
        conversation_history=conversation_history,
        db=db,
    )

    # Handle pipeline errors
    if pipeline_result.error:
        error_msg = await session_manager.add_message(
            session_id=session_id,
            role="assistant",
            content=f"I encountered an error: {pipeline_result.error}",
            error_message=pipeline_result.error,
            db=db,
        )

        await audit_service.log_query(
            db=db,
            user_id=user.id,
            session_id=session_id,
            connection_id=conn.id,
            natural_language_input=body.content,
            sql_generated=pipeline_result.generated_sql,
            error_message=pipeline_result.error,
            ip_address=request.client.host if request.client else None,
            status="error",
        )

        return QueryResponse(
            message=ChatMessageResponse.model_validate(error_msg),
            explanation=pipeline_result.error,
            sql=pipeline_result.generated_sql or None,
        )

    # Success — save results
    sql_executed = pipeline_result.optimized_sql or pipeline_result.generated_sql
    results = pipeline_result.query_results
    if results and results.get("rows") and results.get("columns"):
        raw_rows = results["rows"]
        if raw_rows and isinstance(raw_rows[0], (list, tuple)):
            cols = results["columns"]
            results["rows"] = [dict(zip(cols, r)) for r in raw_rows]
    results_json = safe_json_dumps(results) if results else None
    follow_ups = safe_json_dumps(pipeline_result.follow_up_suggestions) if pipeline_result.follow_up_suggestions else None
    chart_config = safe_json_dumps(pipeline_result.chart_suggestion) if pipeline_result.chart_suggestion else None

    assistant_msg = await session_manager.add_message(
        session_id=session_id,
        role="assistant",
        content=pipeline_result.explanation,
        sql_generated=pipeline_result.generated_sql,
        sql_executed=sql_executed,
        results_json=results_json,
        result_row_count=results.get("row_count") if results else None,
        execution_time_ms=pipeline_result.execution_time_ms,
        confidence_score=pipeline_result.confidence_score,
        confidence_reason=pipeline_result.confidence_reason,
        suggested_chart_type=pipeline_result.chart_suggestion.get("chart_type") if pipeline_result.chart_suggestion else None,
        chart_config_json=chart_config,
        follow_up_suggestions_json=follow_ups,
        db=db,
    )

    # Cache the result
    await semantic_cache.store_cache(
        question=body.content,
        connection_id=conn.id,
        sql=pipeline_result.generated_sql,
        result_json=results_json,
        result_row_count=results.get("row_count") if results else None,
        db=db,
    )

    # Update session title from first question
    if len(conversation_history) <= 1:
        title = body.content[:100] + ("..." if len(body.content) > 100 else "")
        await session_manager.update_session_title(session_id, title, db)

    # Audit log
    await audit_service.log_query(
        db=db,
        user_id=user.id,
        session_id=session_id,
        connection_id=conn.id,
        natural_language_input=body.content,
        sql_generated=pipeline_result.generated_sql,
        sql_executed=sql_executed,
        result_summary=pipeline_result.explanation[:500] if pipeline_result.explanation else None,
        rows_returned=results.get("row_count") if results else None,
        confidence_score=pipeline_result.confidence_score,
        validation_passed=pipeline_result.is_valid,
        execution_time_ms=pipeline_result.execution_time_ms,
        ip_address=request.client.host if request.client else None,
        status="success",
    )

    return QueryResponse(
        message=ChatMessageResponse.model_validate(assistant_msg),
        explanation=pipeline_result.explanation,
        sql=sql_executed,
        results=results.get("rows") if results else None,
        columns=results.get("columns") if results else None,
        row_count=results.get("row_count") if results else None,
        execution_time_ms=pipeline_result.execution_time_ms,
        confidence=pipeline_result.confidence_score,
        confidence_reason=pipeline_result.confidence_reason,
        chart_suggestion=pipeline_result.chart_suggestion,
        follow_up_suggestions=pipeline_result.follow_up_suggestions,
        was_cached=False,
    )


@router.post("/explain-sql", response_model=ExplainSQLResponse)
async def explain_sql(
    body: ExplainSQLRequest,
    user: User = Depends(get_current_user),
):
    """
    'Explain This Query' reverse mode — paste an SQL query
    and get a plain English explanation and clause-by-clause breakdown.
    """
    from app.core.sql_explainer import get_clause_breakdown_list, generate_sql_explanation_html, analyze_sql_clauses

    breakdown = get_clause_breakdown_list(body.sql)
    html_explanation = generate_sql_explanation_html(body.sql)
    clauses = analyze_sql_clauses(body.sql)
    tables = [clauses["from"]] if clauses["from"] else []

    # Calculate complexity
    complexity = "simple"
    if len(clauses.get("joins", [])) > 1 or clauses.get("having"):
        complexity = "complex"
    elif clauses.get("joins") or clauses.get("group_by"):
        complexity = "moderate"

    return ExplainSQLResponse(
        original_sql=body.sql,
        explanation=html_explanation,
        clause_breakdown=breakdown,
        tables_used=tables,
        complexity_rating=complexity,
    )
