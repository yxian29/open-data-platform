from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LineageNode(BaseModel):
    id: UUID
    node_type: str
    dataset_id: UUID | None = None
    table_name: str | None = None
    column_name: str | None = None
    transform_name: str | None = None
    metadata: dict = {}
    created_at: datetime | None = None


class LineageEdge(BaseModel):
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    edge_type: str = "derives_from"
    transform_logic: str | None = None
    pipeline_run_id: UUID | None = None
    created_at: datetime | None = None


class LineageGraph(BaseModel):
    nodes: list[LineageNode] = []
    edges: list[LineageEdge] = []
