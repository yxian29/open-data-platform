from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    rows: list[dict] | None = None
    session_id: str


class SuggestRequest(BaseModel):
    dataset_name: str
    columns: list[dict]


class SuggestResponse(BaseModel):
    suggested_type: str
    suggested_properties: list[dict]
    reasoning: str


class SummarizeRequest(BaseModel):
    dataset_name: str
    table_name: str | None = None
    sample_rows: int = 20


class SummarizeResponse(BaseModel):
    summary: str
    key_insights: list[str]
