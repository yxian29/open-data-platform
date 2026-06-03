from contextlib import asynccontextmanager

from fastapi import FastAPI

from shared.db.neo4j_client import get_driver, close_driver, run_write
from src.routes import types, objects, links


@asynccontextmanager
async def lifespan(app: FastAPI):
    driver = get_driver()
    await _ensure_constraints()
    yield
    await close_driver()


async def _ensure_constraints():
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:ObjectType) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:PropertyType) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (l:LinkType) REQUIRE l.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (o:ObjectInstance) REQUIRE o.id IS UNIQUE",
    ]
    for c in constraints:
        await run_write(c)


app = FastAPI(
    title="Open Data Platform Ontology Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(types.router, prefix="/api/v1/types", tags=["Object Types"])
app.include_router(objects.router, prefix="/api/v1/objects", tags=["Objects"])
app.include_router(links.router, prefix="/api/v1/links", tags=["Links"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ontology-service"}


@app.get("/api/v1/graph")
async def get_full_graph():
    from shared.db.neo4j_client import run_query

    nodes = await run_query(
        """
        MATCH (t:ObjectType)
        OPTIONAL MATCH (t)-[:HAS_PROPERTY]->(p:PropertyType)
        RETURN t.id AS id, t.name AS name, t.description AS description,
               collect(p {.id, .name, .data_type}) AS properties
        """
    )

    edges = await run_query(
        """
        MATCH (s:ObjectType)-[r:LINKED_VIA]->(target:ObjectType)
        RETURN s.id AS source, target.id AS target,
               r.link_type_id AS link_type_id, r.name AS name
        """
    )

    return {"nodes": nodes, "edges": edges}
