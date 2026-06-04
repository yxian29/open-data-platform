"""Seed ChromaDB collections from live data sources on startup."""
import asyncpg
from neo4j import AsyncGraphDatabase
from src.config import settings
from src.vector_store import upsert, get_collection


async def seed_ontology():
    """Embed ObjectType descriptions from Neo4j into 'ontology_embeddings'."""
    col = get_collection("ontology_embeddings")
    if col.count() > 0:
        return  # already seeded

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    try:
        async with driver.session() as session:
            result = await session.run(
                "MATCH (t:ObjectType) RETURN t.id AS id, t.name AS name, t.description AS description"
            )
            records = await result.data()
    finally:
        await driver.close()

    if not records:
        return

    upsert(
        "ontology_embeddings",
        ids=[r["id"] for r in records],
        documents=[f"{r['name']}: {r.get('description', '')}" for r in records],
        metadatas=[{"name": r["name"], "id": r["id"]} for r in records],
    )


async def seed_schemas():
    """Embed dataset schemas from PostgreSQL into 'schema_embeddings'."""
    col = get_collection("schema_embeddings")
    if col.count() > 0:
        return  # already seeded

    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    try:
        rows = await conn.fetch("SELECT id::text, name, schema FROM datasets WHERE schema IS NOT NULL")
    finally:
        await conn.close()

    if not rows:
        return

    ids, documents, metadatas = [], [], []
    for row in rows:
        schema = row["schema"] or {}
        columns = schema.get("columns", [])
        col_text = ", ".join(f"{c.get('name')} ({c.get('type', 'unknown')})" for c in columns)
        ids.append(row["id"])
        documents.append(f"Dataset '{row['name']}' columns: {col_text}")
        metadatas.append({"dataset_id": row["id"], "dataset_name": row["name"]})

    upsert("schema_embeddings", ids=ids, documents=documents, metadatas=metadatas)


async def seed_all():
    try:
        await seed_ontology()
    except Exception as e:
        print(f"[seeder] ontology seed skipped: {e}")
    try:
        await seed_schemas()
    except Exception as e:
        print(f"[seeder] schema seed skipped: {e}")
