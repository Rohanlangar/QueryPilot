"""
QueryPilot — WebSocket Chat Handler

WebSocket endpoint for streaming pipeline responses with real-time
status updates (e.g., "Understanding schema...", "Generating SQL...").
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, async_session_factory
from app.models.connection import Connection
from app.models.user import User
from app.core.security import decode_access_token
from app.services.session_manager import session_manager
from app.services.pipeline import agent_pipeline
from app.services.connection_manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


class ConnectionManagerWS:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_json(self, client_id: str, data: dict):
        ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_json(data)


ws_manager = ConnectionManagerWS()


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
):
    """
    WebSocket endpoint for streaming chat responses.

    Protocol:
      Client sends: {"token": "jwt...", "message": "question text"}
      Server sends:
        {"type": "status", "message": "Understanding schema..."}
        {"type": "status", "message": "Generating SQL..."}
        {"type": "status", "message": "Executing query..."}
        {"type": "result", "data": {...full QueryResponse...}}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()
    client_id = f"ws_{session_id}"

    try:
        while True:
            # Receive message from client
            raw = await websocket.receive_text()
            data = json.loads(raw)

            # Authenticate
            token = data.get("token")
            if not token:
                await websocket.send_json({"type": "error", "message": "No auth token provided"})
                continue

            try:
                payload = decode_access_token(token)
                user_id = payload.get("sub")
            except Exception:
                await websocket.send_json({"type": "error", "message": "Invalid token"})
                continue

            message = data.get("message", "").strip()
            if not message:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            # Create status callback for streaming stage updates
            async def on_status(status_payload):
                if isinstance(status_payload, dict):
                    await websocket.send_json(status_payload)
                else:
                    await websocket.send_json({"type": "status", "message": str(status_payload)})

            # Run pipeline with streaming status
            async with async_session_factory() as db:
                try:
                    # Get session
                    session = await session_manager.get_session(session_id, db)
                    if not session or session.user_id != user_id:
                        await websocket.send_json({"type": "error", "message": "Session not found"})
                        continue

                    # Get connection
                    result = await db.execute(
                        select(Connection).where(Connection.id == session.connection_id)
                    )
                    conn = result.scalar_one_or_none()
                    if not conn:
                        await websocket.send_json({"type": "error", "message": "Connection not found"})
                        continue

                    # Save user message
                    await session_manager.add_message(
                        session_id=session_id, role="user", content=message, db=db
                    )

                    # Ensure engine
                    await connection_manager.create_engine(conn)

                    # Run pipeline
                    pipeline_result = await agent_pipeline.run(
                        query=message,
                        connection_id=conn.id,
                        db_type=conn.db_type,
                        db=db,
                        on_status=on_status,
                    )

                    if pipeline_result.error:
                        await websocket.send_json({
                            "type": "error",
                            "message": pipeline_result.error,
                        })
                    else:
                        sql_executed = pipeline_result.optimized_sql or pipeline_result.generated_sql
                        results = pipeline_result.query_results
                        results_json = json.dumps(results) if results else None
                        follow_ups = json.dumps(pipeline_result.follow_up_suggestions) if pipeline_result.follow_up_suggestions else None
                        chart_config = json.dumps(pipeline_result.chart_suggestion) if pipeline_result.chart_suggestion else None

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

                        await websocket.send_json({
                            "type": "result",
                            "data": {
                                "message": {
                                    "id": assistant_msg.id,
                                    "role": assistant_msg.role,
                                    "content": assistant_msg.content,
                                    "created_at": assistant_msg.created_at.isoformat() if hasattr(assistant_msg.created_at, "isoformat") else str(assistant_msg.created_at),
                                },
                                "explanation": pipeline_result.explanation,
                                "sql": sql_executed,
                                "results": results.get("rows") if results else None,
                                "columns": results.get("columns") if results else None,
                                "row_count": results.get("row_count") if results else None,
                                "execution_time_ms": pipeline_result.execution_time_ms,
                                "confidence": pipeline_result.confidence_score,
                                "confidence_reason": pipeline_result.confidence_reason,
                                "chart_suggestion": pipeline_result.chart_suggestion,
                                "follow_up_suggestions": pipeline_result.follow_up_suggestions,
                            },
                        })

                    await db.commit()

                except Exception as e:
                    await db.rollback()
                    logger.error(f"WebSocket pipeline error: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Pipeline error: {str(e)}",
                    })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        ws_manager.disconnect(client_id)
