from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditEvent(BaseModel):
    user_id: str = "anonymous"
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict = {}
    ip_address: str | None = None
    user_agent: str | None = None
    session_id: str | None = None
    status: str = "success"
    duration_ms: int | None = None


class AuditEventResponse(AuditEvent):
    id: UUID
    created_at: datetime


class AuditQueryParams(BaseModel):
    user_id: str | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = 50
    offset: int = 0


class AuditStats(BaseModel):
    total_events: int
    by_action: dict[str, int] = {}
    by_resource_type: dict[str, int] = {}
    by_user: dict[str, int] = {}


class RetentionPolicy(BaseModel):
    id: UUID
    resource_type: str
    retention_days: int
    created_at: datetime


class RetentionPolicyUpdate(BaseModel):
    retention_days: int
