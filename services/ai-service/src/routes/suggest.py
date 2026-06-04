import json
from fastapi import APIRouter
from pydantic import BaseModel
from src.llm import chat as llm_chat
from src.context import get_ontology_types

router = APIRouter()


class SuggestRequest(BaseModel):
    dataset_name: str
    columns: list[dict]  # [{"name": "...", "type": "..."}]


class SuggestResponse(BaseModel):
    suggested_type: str
    suggested_properties: list[dict]
    reasoning: str


SUGGEST_PROMPT = """You are an AI assistant for a semantic data platform.
Given a dataset's column names and types, suggest a business ontology type name and property mappings.
Respond in this exact JSON format (no markdown, no extra text):
{"suggested_type": "<ObjectType name>", "suggested_properties": [{"column": "...", "property": "...", "data_type": "..."}], "reasoning": "<brief explanation>"}
"""


@router.post("", response_model=SuggestResponse)
async def suggest(req: SuggestRequest):
    existing = await get_ontology_types()
    col_summary = ", ".join(f"{c['name']} ({c.get('type', '?')})" for c in req.columns)

    prompt = f"""{SUGGEST_PROMPT}

Existing ontology types for reference:
{existing}

Dataset name: {req.dataset_name}
Columns: {col_summary}"""

    raw = await llm_chat(prompt)

    try:
        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(clean)
        return SuggestResponse(
            suggested_type=parsed.get("suggested_type", "Unknown"),
            suggested_properties=parsed.get("suggested_properties", []),
            reasoning=parsed.get("reasoning", ""),
        )
    except Exception:
        return SuggestResponse(suggested_type="Unknown", suggested_properties=[], reasoning=raw)
