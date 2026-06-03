from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class PipelineCreate(BaseModel):
    name: str
    description: str = ""
    pipeline_type: str = "dbt"
    config: dict = {}
    schedule: str | None = None


class PipelineResponse(BaseModel):
    id: UUID
    name: str
    description: str
    pipeline_type: str
    config: dict = {}
    schedule: str | None = None
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime


class PipelineRunResponse(BaseModel):
    id: UUID
    pipeline_id: UUID
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    logs: str = ""
    error: str | None = None
    created_at: datetime


class PipelineTriggerRequest(BaseModel):
    config_overrides: dict = {}
