"""
Chat schemas — request/response models for chat and query endpoints.
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    """Create a new chat session."""
    connection_id: str
    title: Optional[str] = "New Conversation"


class ChatMessageCreate(BaseModel):
    """Send a message (question) in a chat session."""
    content: str = Field(..., min_length=1, max_length=5000, examples=["What were the top 10 products by revenue last month?"])


class ExplainSQLRequest(BaseModel):
    """Request to explain an existing SQL query in plain English."""
    sql: str = Field(..., min_length=1, examples=["SELECT p.name, SUM(o.amount) FROM products p JOIN orders o ON p.id = o.product_id GROUP BY p.name ORDER BY SUM(o.amount) DESC LIMIT 10"])
    connection_id: Optional[str] = None  # Optional: provides schema context


# ── Responses ─────────────────────────────────────────────────

class ChatMessageResponse(BaseModel):
    """A single chat message."""
    id: str
    session_id: str
    role: str
    content: str
    sql_generated: Optional[str] = None
    sql_executed: Optional[str] = None
    results_json: Optional[str] = None
    result_row_count: Optional[int] = None
    execution_time_ms: Optional[float] = None
    confidence_score: Optional[float] = None
    confidence_reason: Optional[str] = None
    suggested_chart_type: Optional[str] = None
    chart_config_json: Optional[str] = None
    follow_up_suggestions_json: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    """Chat session summary."""
    id: str
    connection_id: str
    title: str
    summary: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None

    model_config = {"from_attributes": True}


class ChatSessionDetailResponse(BaseModel):
    """Chat session with messages."""
    id: str
    connection_id: str
    title: str
    summary: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []

    model_config = {"from_attributes": True}


class QueryResponse(BaseModel):
    """Full response to a user query — the main chat response payload."""
    message: ChatMessageResponse
    explanation: str
    sql: Optional[str] = None
    results: Optional[List[Any]] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[float] = None
    confidence: Optional[float] = None
    confidence_reason: Optional[str] = None
    chart_suggestion: Optional[dict] = None
    follow_up_suggestions: Optional[List[str]] = None
    was_cached: bool = False


class ExplainSQLResponse(BaseModel):
    """Response from the 'Explain This Query' reverse mode."""
    original_sql: str
    explanation: str
    clause_breakdown: Optional[List[dict]] = None  # Per-clause explanation
    tables_used: Optional[List[str]] = None
    complexity_rating: Optional[str] = None  # "simple", "moderate", "complex"
