import httpx
from shared.config import settings

_HTTP_BASE = None


def _base_url() -> str:
    global _HTTP_BASE
    if _HTTP_BASE is None:
        _HTTP_BASE = f"http://{settings.clickhouse_host}:8123"
    return _HTTP_BASE


def _params() -> dict:
    return {
        "user": settings.clickhouse_user,
        "password": settings.clickhouse_password,
        "database": settings.clickhouse_db,
        "output_format_json_quote_64bit_integers": 0,
    }


def run_query(sql: str) -> list[dict]:
    """Execute SQL via ClickHouse HTTP API and return rows as list of dicts."""
    with httpx.Client(timeout=30) as client:
        r = client.post(
            _base_url(),
            params={**_params(), "query": sql + " FORMAT JSONEachRow"},
        )
        if r.status_code != 200:
            raise RuntimeError(r.text.strip())
        if not r.text.strip():
            return []
        rows = []
        for line in r.text.strip().splitlines():
            import json
            rows.append(json.loads(line))
        return rows
