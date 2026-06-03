from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.db.clickhouse_client import execute_query

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


@router.post("/query")
async def run_query(body: QueryRequest):
    query = body.query.strip()

    normalized = query.upper()
    if any(kw in normalized for kw in ["DROP", "ALTER", "TRUNCATE", "CREATE", "INSERT", "DELETE", "UPDATE"]):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

    try:
        results = await execute_query(query)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
