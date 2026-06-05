import httpx
from fastapi import APIRouter, HTTPException

from shared.db.postgres import get_connection

router = APIRouter()


@router.get("/graph")
async def get_lineage_graph():
    async with get_connection() as conn:
        nodes = await conn.fetch("SELECT * FROM lineage_nodes ORDER BY table_name, column_name")
        edges = await conn.fetch("SELECT * FROM lineage_edges")

    return {
        "nodes": [dict(n) for n in nodes],
        "edges": [dict(e) for e in edges],
    }


@router.get("/column/{table}/{column}")
async def get_column_lineage(table: str, column: str):
    async with get_connection() as conn:
        node = await conn.fetchrow(
            "SELECT * FROM lineage_nodes WHERE table_name = $1 AND column_name = $2",
            table, column,
        )
        if not node:
            raise HTTPException(status_code=404, detail="Column not found in lineage graph")

        node_id = node["id"]

        upstream = await conn.fetch(
            """
            WITH RECURSIVE upstream AS (
                SELECT e.source_node_id, e.target_node_id, e.edge_type, e.transform_logic, 1 as depth
                FROM lineage_edges e WHERE e.target_node_id = $1
                UNION ALL
                SELECT e.source_node_id, e.target_node_id, e.edge_type, e.transform_logic, u.depth + 1
                FROM lineage_edges e
                JOIN upstream u ON e.target_node_id = u.source_node_id
                WHERE u.depth < 10
            )
            SELECT DISTINCT n.* FROM upstream u
            JOIN lineage_nodes n ON n.id = u.source_node_id
            """,
            node_id,
        )

        downstream = await conn.fetch(
            """
            WITH RECURSIVE downstream AS (
                SELECT e.source_node_id, e.target_node_id, e.edge_type, e.transform_logic, 1 as depth
                FROM lineage_edges e WHERE e.source_node_id = $1
                UNION ALL
                SELECT e.source_node_id, e.target_node_id, e.edge_type, e.transform_logic, d.depth + 1
                FROM lineage_edges e
                JOIN downstream d ON e.source_node_id = d.target_node_id
                WHERE d.depth < 10
            )
            SELECT DISTINCT n.* FROM downstream d
            JOIN lineage_nodes n ON n.id = d.target_node_id
            """,
            node_id,
        )

    return {
        "node": dict(node),
        "upstream": [dict(n) for n in upstream],
        "downstream": [dict(n) for n in downstream],
    }


@router.get("/dataset/{dataset_id}")
async def get_dataset_lineage(dataset_id: str):
    async with get_connection() as conn:
        nodes = await conn.fetch(
            "SELECT * FROM lineage_nodes WHERE dataset_id = $1",
            dataset_id,
        )
        if not nodes:
            return {"nodes": [], "edges": []}

        node_ids = [n["id"] for n in nodes]
        edges = await conn.fetch(
            """
            SELECT * FROM lineage_edges
            WHERE source_node_id = ANY($1) OR target_node_id = ANY($1)
            """,
            node_ids,
        )

    return {
        "nodes": [dict(n) for n in nodes],
        "edges": [dict(e) for e in edges],
    }


@router.post("/refresh")
async def refresh_lineage():
    """Proxy to pipeline service which has access to the dbt directory."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post("http://pipeline-service:8002/lineage/refresh")
        resp.raise_for_status()
        return resp.json()
