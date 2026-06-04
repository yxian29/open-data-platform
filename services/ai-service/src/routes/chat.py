import json
import uuid
import asyncpg
from fastapi import APIRouter
from pydantic import BaseModel
from src.config import settings
from src.llm import chat as llm_chat
from src.context import get_dataset_schemas, get_ontology_types, get_clickhouse_tables
from shared.db.clickhouse import run_query

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    rows: list[dict] | None = None
    session_id: str


SYSTEM_PROMPT = """You are an AI assistant for an Open Data Platform backed by ClickHouse 25.x.
Rules — follow every one of these exactly:
1. ONLY query tables listed under "ClickHouse tables". If the list says no tables exist, set sql to null.
2. ALWAYS use fully-qualified names: odp.customers, odp.orders, odp.products — never bare names.
3. JOIN syntax for ClickHouse 25.x: do NOT assign short aliases to tables (AS c, AS o, etc.).
   Reference columns using the table name itself: customers.id, orders.customer_id.
   Example of correct JOIN:
     SELECT customers.id, customers.name
     FROM odp.customers
     INNER JOIN odp.orders ON customers.id = orders.customer_id
4. Never invent table or column names not shown in the context below.
Always respond in this exact JSON format (no markdown fences, no extra text):
{"answer": "<plain English explanation>", "sql": "<ClickHouse SQL or null>"}
"""


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    schemas = await get_dataset_schemas()
    ontology = await get_ontology_types()
    ch_tables = get_clickhouse_tables()

    prompt = f"""{SYSTEM_PROMPT}

ClickHouse tables (only query these):
{ch_tables}

Registered dataset schemas (metadata only, not necessarily in ClickHouse):
{schemas}

Ontology object types:
{ontology}

User question: {req.query}"""

    raw = await llm_chat(prompt)

    try:
        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(clean)
        answer = parsed.get("answer", raw)
        sql = parsed.get("sql") or None
    except Exception:
        answer = raw
        sql = None

    rows = None
    if sql:
        try:
            rows = run_query(sql)
        except Exception as e:
            answer += f"\n\n(SQL execution failed: {e})"
            sql = None

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
            session_id, "assistant", answer, json.dumps({"sql": sql, "rows": rows}),
        )
        await conn.close()
    except Exception:
        pass

    return ChatResponse(answer=answer, sql=sql, rows=rows, session_id=session_id)


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
