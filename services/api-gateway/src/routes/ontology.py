from fastapi import APIRouter, HTTPException
import httpx

from shared.config import settings

router = APIRouter()

ONTOLOGY_SERVICE_URL = "http://ontology-service:8001"


async def _proxy(method: str, path: str, **kwargs):
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{ONTOLOGY_SERVICE_URL}{path}"
        response = await client.request(method, url, **kwargs)
        return response.json()


@router.get("/types")
async def list_types():
    return await _proxy("GET", "/api/v1/types")


@router.post("/types")
async def create_type(body: dict):
    return await _proxy("POST", "/api/v1/types", json=body)


@router.get("/types/{type_id}")
async def get_type(type_id: str):
    return await _proxy("GET", f"/api/v1/types/{type_id}")


@router.delete("/types/{type_id}")
async def delete_type(type_id: str):
    return await _proxy("DELETE", f"/api/v1/types/{type_id}")


@router.post("/types/{type_id}/properties")
async def add_property(type_id: str, body: dict):
    return await _proxy("POST", f"/api/v1/types/{type_id}/properties", json=body)


@router.delete("/types/{type_id}/properties/{prop_id}")
async def delete_property(type_id: str, prop_id: str):
    return await _proxy("DELETE", f"/api/v1/types/{type_id}/properties/{prop_id}")


@router.post("/types/{type_id}/links")
async def add_link(type_id: str, body: dict):
    return await _proxy("POST", f"/api/v1/types/{type_id}/links", json=body)


@router.post("/types/{type_id}/map")
async def map_dataset(type_id: str, body: dict):
    return await _proxy("POST", f"/api/v1/types/{type_id}/map", json=body)


@router.get("/objects")
async def query_objects(type_id: str | None = None, limit: int = 50, offset: int = 0):
    params = {"limit": limit, "offset": offset}
    if type_id:
        params["type_id"] = type_id
    return await _proxy("GET", "/api/v1/objects", params=params)


@router.get("/objects/{object_id}")
async def get_object(object_id: str):
    return await _proxy("GET", f"/api/v1/objects/{object_id}")


@router.get("/objects/{object_id}/neighbors")
async def get_neighbors(object_id: str):
    return await _proxy("GET", f"/api/v1/objects/{object_id}/neighbors")


@router.get("/graph")
async def get_graph():
    return await _proxy("GET", "/api/v1/graph")
