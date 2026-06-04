from fastapi import APIRouter
from pydantic import BaseModel
from src.llm import chat as llm_chat
from shared.db.clickhouse import run_query

router = APIRouter()


class SummarizeRequest(BaseModel):
    dataset_name: str
    table_name: str | None = None  # ClickHouse table; defaults to dataset_name
    sample_rows: int = 20


class SummarizeResponse(BaseModel):
    summary: str
    key_insights: list[str]


SUMMARIZE_PROMPT = """You are a data analyst. Given a sample of rows from a dataset, write a concise summary and list 3-5 key insights.
Respond in JSON (no markdown):
{{"summary": "...", "key_insights": ["...", "..."]}}
"""


@router.post("", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest):
    table = req.table_name or req.dataset_name.lower().replace(" ", "_")

    try:
        rows = run_query(f"SELECT * FROM {table} LIMIT {req.sample_rows}")
        sample_text = "\n".join(str(r) for r in rows[:req.sample_rows])
    except Exception as e:
        sample_text = f"(Could not fetch sample: {e})"

    prompt = f"""{SUMMARIZE_PROMPT}

Dataset: {req.dataset_name}
Sample data ({req.sample_rows} rows):
{sample_text}"""

    raw = await llm_chat(prompt)

    import json
    try:
        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(clean)
        return SummarizeResponse(
            summary=parsed.get("summary", raw),
            key_insights=parsed.get("key_insights", []),
        )
    except Exception:
        return SummarizeResponse(summary=raw, key_insights=[])
