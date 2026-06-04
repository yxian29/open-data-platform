"""Fetch schema and ontology context to inject into Claude prompts."""
import asyncpg
import httpx
from src.config import settings

ONTOLOGY_SERVICE_URL = "http://ontology-service:8001"


def get_clickhouse_tables() -> str:
    """Return tables that actually exist in ClickHouse via HTTP API."""
    try:
        with httpx.Client(timeout=5) as client:
            r = client.post(
                f"http://{settings.clickhouse_host}:8123",
                params={
                    "user": settings.clickhouse_user,
                    "password": settings.clickhouse_password,
                    "query": f"SHOW TABLES FROM {settings.clickhouse_db}",
                },
            )
            tables = [t.strip() for t in r.text.strip().splitlines() if t.strip()]
        if not tables:
            return "NO TABLES EXIST IN CLICKHOUSE. You MUST set sql to null."
        return "\n".join(f"- {settings.clickhouse_db}.{t}" for t in tables)
    except Exception as e:
        return f"CLICKHOUSE UNAVAILABLE ({e}). You MUST set sql to null."


async def get_dataset_schemas() -> str:
    """Return a text summary of all dataset schemas from PostgreSQL."""
    try:
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        rows = await conn.fetch(
            "SELECT name, schema_info FROM datasets "
            "WHERE schema_info IS NOT NULL AND schema_info != '{}'::jsonb "
            "ORDER BY created_at DESC LIMIT 20"
        )
        await conn.close()
    except Exception as e:
        return f"(Could not fetch dataset schemas: {e})"

    if not rows:
        return "(No datasets registered yet)"

    lines = []
    for row in rows:
        schema = row["schema_info"] or {}
        if isinstance(schema, str):
            import json
            schema = json.loads(schema)
        columns = schema.get("columns", [])
        col_text = ", ".join(f"{c.get('name')} {c.get('data_type', '')}" for c in columns)
        lines.append(f"- {row['name']}: {col_text}")
    return "\n".join(lines)


async def get_ontology_types() -> str:
    """Return a text summary of ontology object types from the ontology service."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{ONTOLOGY_SERVICE_URL}/api/v1/types")
            types = resp.json()
    except Exception as e:
        return f"(Could not fetch ontology types: {e})"

    if not types:
        return "(No ontology types defined yet)"

    lines = [f"- {t.get('name', '?')}: {t.get('description', '')}" for t in types]
    return "\n".join(lines)
