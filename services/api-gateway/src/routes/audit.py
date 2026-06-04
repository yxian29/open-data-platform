import httpx
from fastapi import APIRouter, Depends, Request

from src.middleware.auth import get_current_user, require_role

router = APIRouter()

AUDIT_SERVICE_URL = "http://audit-service:8003"


async def _proxy(method: str, path: str, request: Request, body: dict | None = None):
    url = f"{AUDIT_SERVICE_URL}/api/v1{path}"
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, url, params=params, json=body)
        return resp.json()


@router.get("/events")
async def list_events(request: Request, _user=Depends(get_current_user)):
    return await _proxy("GET", "/events", request)


@router.get("/events/{event_id}")
async def get_event(event_id: str, request: Request, _user=Depends(get_current_user)):
    return await _proxy("GET", f"/events/{event_id}", request)


@router.get("/stats")
async def get_stats(request: Request, _user=Depends(get_current_user)):
    return await _proxy("GET", "/stats", request)


@router.get("/retention")
async def list_retention(request: Request, _user=Depends(require_role("admin"))):
    return await _proxy("GET", "/retention", request)


@router.put("/retention/{policy_id}")
async def update_retention(policy_id: str, request: Request, _user=Depends(require_role("admin"))):
    body = await request.json()
    return await _proxy("PUT", f"/retention/{policy_id}", request, body)


@router.post("/purge")
async def purge(request: Request, _user=Depends(require_role("admin"))):
    return await _proxy("POST", "/purge", request)
