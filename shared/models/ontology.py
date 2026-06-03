from datetime import datetime
from pydantic import BaseModel


class PropertyTypeCreate(BaseModel):
    name: str
    data_type: str = "string"
    required: bool = False
    description: str = ""


class PropertyTypeResponse(BaseModel):
    id: str
    name: str
    data_type: str
    required: bool
    description: str = ""


class LinkTypeCreate(BaseModel):
    name: str
    target_type_id: str
    cardinality: str = "many-to-many"
    description: str = ""


class LinkTypeResponse(BaseModel):
    id: str
    name: str
    target_type_id: str
    target_type_name: str = ""
    cardinality: str
    description: str = ""


class ObjectTypeCreate(BaseModel):
    name: str
    description: str = ""


class ObjectTypeResponse(BaseModel):
    id: str
    name: str
    description: str
    version: int = 1
    properties: list[PropertyTypeResponse] = []
    links: list[LinkTypeResponse] = []
    created_at: str = ""


class DatasetMappingRequest(BaseModel):
    dataset_id: str
    column_mappings: dict[str, str]


class ObjectInstanceResponse(BaseModel):
    id: str
    type_id: str
    type_name: str = ""
    properties: dict = {}
    source_dataset: str = ""
    created_at: str = ""


class ObjectQueryRequest(BaseModel):
    type_id: str | None = None
    filters: dict = {}
    limit: int = 50
    offset: int = 0
