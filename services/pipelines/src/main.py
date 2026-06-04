from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from shared.db.postgres import get_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Open Data Platform Pipeline Service",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "pipeline-service"}


@app.post("/lineage/refresh")
async def refresh_lineage():
    from src.lineage_parser import build_lineage_graph
    from shared.db.postgres import get_connection

    dbt_dir = Path("/app/dbt")
    if not dbt_dir.exists():
        return {"nodes_created": 0, "edges_created": 0, "warning": "dbt directory not found"}

    graph = build_lineage_graph(str(dbt_dir))

    async with get_connection() as conn:
        await conn.execute("DELETE FROM lineage_edges")
        await conn.execute("DELETE FROM lineage_nodes")

        node_id_map = {}
        for i, node in enumerate(graph["nodes"]):
            row = await conn.fetchrow(
                """
                INSERT INTO lineage_nodes (node_type, table_name, column_name, transform_name, metadata)
                VALUES ($1, $2, $3, $4, '{}')
                RETURNING id
                """,
                node["node_type"], node["table_name"],
                node.get("column_name"), node.get("transform_name"),
            )
            node_id_map[i] = row["id"]

        for edge in graph["edges"]:
            source_id = node_id_map[edge["source"]]
            target_id = node_id_map[edge["target"]]
            await conn.execute(
                """
                INSERT INTO lineage_edges (source_node_id, target_node_id, edge_type)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                """,
                source_id, target_id, edge["edge_type"],
            )

    return {
        "nodes_created": len(graph["nodes"]),
        "edges_created": len(graph["edges"]),
    }
