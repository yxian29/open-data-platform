from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    sample_values: list[str] = []


class DatasetSchema(BaseModel):
    columns: list[ColumnInfo] = []


class DatasetCreate(BaseModel):
    name: str
    description: str = ""


class DatasetResponse(BaseModel):
    id: UUID
    name: str
    description: str
    source_type: str
    storage_path: str
    schema_info: DatasetSchema | dict = {}
    row_count: int = 0
    file_size_bytes: int = 0
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime
