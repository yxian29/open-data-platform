import httpx
from shared.config import settings


def get_clickhouse_url() -> str:
    return f"http://{settings.clickhouse_host}:{settings.clickhouse_port}/"


def _raise_for_clickhouse_error(response: httpx.Response) -> None:
    if not response.is_success:
        body = response.text.strip()
        raise httpx.HTTPStatusError(
            body or f"HTTP {response.status_code}",
            request=response.request,
            response=response,
        )


async def execute_query(query: str, fmt: str = "JSONEachRow") -> list[dict]:
    url = get_clickhouse_url()
    params = {
        "database": settings.clickhouse_db,
        "user": settings.clickhouse_user,
        "password": settings.clickhouse_password,
    }
    full_query = f"{query} FORMAT {fmt}" if "FORMAT" not in query.upper() else query

    async with httpx.AsyncClient() as client:
        response = await client.post(url, params=params, content=full_query)
        _raise_for_clickhouse_error(response)
        if not response.text.strip():
            return []
        import json
        return [json.loads(line) for line in response.text.strip().split("\n") if line]


async def execute_command(query: str) -> str:
    url = get_clickhouse_url()
    params = {
        "database": settings.clickhouse_db,
        "user": settings.clickhouse_user,
        "password": settings.clickhouse_password,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, params=params, content=query)
        _raise_for_clickhouse_error(response)
        return response.text
