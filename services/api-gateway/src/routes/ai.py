import httpx
from fastapi import APIRouter, Depends, Request
from src.middleware.auth import get_current_user

router = APIRouter()

AI_SERVICE_URL = "http://ai-service:8004"


async def _proxy(method: str, path: str, request: Request, body: dict | None = None):
    url = f"{AI_SERVICE_URL}/api/v1{path}"
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.request(method, url, params=params, json=body)
        return resp.json()


@router.get("/health")
async def ai_health():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{AI_SERVICE_URL}/health")
        return resp.json()


@router.post("/chat")
async def chat(request: Request, _user=Depends(get_current_user)):
    body = await request.json()
    return await _proxy("POST", "/chat", request, body)


@router.post("/suggest")
async def suggest(request: Request, _user=Depends(get_current_user)):
    body = await request.json()
    return await _proxy("POST", "/suggest", request, body)


@router.post("/summarize")
async def summarize(request: Request, _user=Depends(get_current_user)):
    body = await request.json()
    return await _proxy("POST", "/summarize", request, body)


@router.get("/history/{session_id}")
async def get_history(session_id: str, request: Request, _user=Depends(get_current_user)):
    return await _proxy("GET", f"/chat/history/{session_id}", request)
