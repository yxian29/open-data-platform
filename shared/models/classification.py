from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class ClassificationLevel(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class ClassificationCreate(BaseModel):
    column_name: str | None = None
    classification: ClassificationLevel
    reason: str = ""


class ClassificationResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    column_name: str | None = None
    classification: ClassificationLevel
    reason: str
    classified_by: str
    classified_at: datetime
    auto_detected: bool


class ClassificationRuleCreate(BaseModel):
    name: str
    pattern: str
    match_type: str = "column_name"
    classification: ClassificationLevel
    enabled: bool = True


class ClassificationRuleResponse(ClassificationRuleCreate):
    id: UUID
    created_at: datetime


class ClassificationRuleUpdate(BaseModel):
    name: str | None = None
    pattern: str | None = None
    classification: ClassificationLevel | None = None
    enabled: bool | None = None


class ClassificationSummary(BaseModel):
    dataset_id: UUID
    dataset_name: str
    overall_classification: ClassificationLevel | None = None
    column_count: int = 0
    classified_count: int = 0
