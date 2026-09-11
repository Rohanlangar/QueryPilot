"""
Audit schemas — request/response models for audit trail endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Single audit log entry."""
    id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    connection_id: Optional[str] = None
    action: str
    natural_language_input: Optional[str] = None
    sql_generated: Optional[str] = None
    sql_executed: Optional[str] = None
    result_summary: Optional[str] = None
    rows_returned: Optional[int] = None
    confidence_score: Optional[float] = None
    validation_passed: Optional[bool] = None
    was_cached: bool = False
    execution_time_ms: Optional[float] = None
    ip_address: Optional[str] = None
    error_message: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Paginated audit log list."""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditStats(BaseModel):
    """Aggregate audit statistics."""
    total_queries: int
    queries_today: int
    queries_this_week: int
    avg_execution_time_ms: Optional[float] = None
    cache_hit_rate: Optional[float] = None
    top_users: List[dict] = []       # [{user_id, username, query_count}]
    top_tables: List[dict] = []      # [{table_name, query_count}]
    error_rate: Optional[float] = None
