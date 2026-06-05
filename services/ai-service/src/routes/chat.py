import json
import uuid
import asyncpg
from fastapi import APIRouter
from pydantic import BaseModel
from src.config import settings
from src.llm import chat as llm_chat
from src.context import get_dataset_schemas, get_ontology_graph, get_clickhouse_tables
from shared.db.clickhouse import run_query
from shared.db.neo4j_client import run_query as neo4j_query

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    rows: list[dict] | None = None
    cypher: str | None = None
    graph_result: list[dict] | None = None
    session_id: str


_CYPHER_WRITE_KEYWORDS = {"CREATE", "DELETE", "DETACH", "SET", "REMOVE", "MERGE"}


def _is_read_only_cypher(cypher: str) -> bool:
    tokens = cypher.upper().split()
    return not any(kw in tokens for kw in _CYPHER_WRITE_KEYWORDS)


SYSTEM_PROMPT = """You are an AI assistant for an Open Data Platform with two data backends:

1. **ClickHouse** (analytical data) — contains actual data rows in denormalized tables.
   Use for: counts, aggregations, filtering, joins on tabular data.
2. **Neo4j** (ontology schema) — contains type definitions, properties, and relationship definitions.
   It does NOT contain instance/row data. Use for: "what types exist?", "how is X related to Y?",
   "what properties does type Z have?", "show the path from type A to type B".

Rules — follow every one exactly:
1. For data/analytical questions → generate ClickHouse SQL. For ontology/schema/relationship questions → generate Cypher.
2. ONLY query ClickHouse tables listed below. If the list says no tables exist, set sql to null.
3. ALWAYS use fully-qualified ClickHouse names: odp.tablename — never bare names.
4. ClickHouse 25.x: do NOT use short table aliases (AS c, AS o). Reference columns by full table name.
5. For Cypher: query ObjectType, PropertyType nodes and LINKED_VIA, HAS_PROPERTY relationships.
   Do NOT query ObjectInstance — no instance data exists in Neo4j.
6. Never invent table, column, type, or relationship names not shown in the context below.

Always respond in this exact JSON format (no markdown fences, no extra text):
{"answer": "<plain English explanation>", "sql": "<ClickHouse SQL or null>", "cypher": "<Cypher or null>"}
"""


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    schemas = await get_dataset_schemas()
    ontology_graph = await get_ontology_graph()
    ch_tables = get_clickhouse_tables()

    prompt = f"""{SYSTEM_PROMPT}

ClickHouse tables (only query these):
{ch_tables}

Registered dataset schemas (metadata only, not necessarily in ClickHouse):
{schemas}

Ontology graph (types, properties, relationships in Neo4j):
{ontology_graph}

User question: {req.query}"""

    raw = await llm_chat(prompt)

    try:
        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(clean)
        answer = parsed.get("answer", raw)
        sql = parsed.get("sql") or None
        cypher = parsed.get("cypher") or None
    except Exception:
        answer = raw
        sql = None
        cypher = None

    rows = None
    if sql:
        try:
            rows = run_query(sql)
        except Exception as e:
            answer += f"\n\n(SQL execution failed: {e})"
            sql = None

    graph_result = None
    if cypher:
        if not _is_read_only_cypher(cypher):
            answer += "\n\n(Cypher query rejected: write operations not permitted.)"
            cypher = None
        else:
            try:
                graph_result = await neo4j_query(cypher)
            except Exception as e:
                answer += f"\n\n(Cypher execution failed: {e})"
                cypher = None

    # Persist conversation turn (best-effort)
    try:
        conn = await asyncpg.connect(
            host=settings.postgres_host, port=settings.postgres_port,
            database=settings.postgres_db, user=settings.postgres_user,
            password=settings.postgres_password,
        )
        await conn.execute(
            "INSERT INTO ai_conversations (session_id, role, content, metadata) VALUES ($1,$2,$3,$4::jsonb)",
            session_id, "user", req.query, "{}",
        )
        await conn.execute(
            "INSERT INTO ai_conversations (session_id, role, content, metadata) VALUES ($1,$2,$3,$4::jsonb)",
            session_id, "assistant", answer,
            json.dumps({"sql": sql, "rows": rows, "cypher": cypher, "graph_result": graph_result}),
        )
        await conn.close()
    except Exception:
        pass

    return ChatResponse(
        answer=answer, sql=sql, rows=rows,
        cypher=cypher, graph_result=graph_result, session_id=session_id,
    )


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    conn = await asyncpg.connect(
        host=settings.postgres_host, port=settings.postgres_port,
        database=settings.postgres_db, user=settings.postgres_user,
        password=settings.postgres_password,
    )
    rows = await conn.fetch(
        "SELECT role, content, metadata, created_at FROM ai_conversations "
        "WHERE session_id=$1 ORDER BY created_at",
        session_id,
    )
    await conn.close()
    result = []
    for r in rows:
        row = dict(r)
        meta = row.get("metadata", {})
        if isinstance(meta, str):
            meta = json.loads(meta)
        row["metadata"] = meta
        result.append(row)
    return result
