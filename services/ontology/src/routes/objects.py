import uuid

from fastapi import APIRouter, HTTPException, Query

from shared.db.neo4j_client import run_query, run_write
from shared.models.ontology import ObjectInstanceResponse

router = APIRouter()


@router.get("", response_model=list[ObjectInstanceResponse])
async def query_objects(
    type_id: str | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
):
    if type_id:
        results = await run_query(
            """
            MATCH (o:ObjectInstance {type_id: $type_id})
            OPTIONAL MATCH (t:ObjectType {id: $type_id})
            RETURN o, t.name AS type_name
            ORDER BY o.created_at DESC
            SKIP $offset LIMIT $limit
            """,
            {"type_id": type_id, "offset": offset, "limit": limit},
        )
    else:
        results = await run_query(
            """
            MATCH (o:ObjectInstance)
            OPTIONAL MATCH (t:ObjectType {id: o.type_id})
            RETURN o, t.name AS type_name
            ORDER BY o.created_at DESC
            SKIP $offset LIMIT $limit
            """,
            {"offset": offset, "limit": limit},
        )

    return [
        ObjectInstanceResponse(
            id=r["o"]["id"],
            type_id=r["o"]["type_id"],
            type_name=r.get("type_name", ""),
            properties=r["o"].get("properties", {}),
            source_dataset=r["o"].get("source_dataset", ""),
            created_at=str(r["o"].get("created_at", "")),
        )
        for r in results
    ]


@router.get("/{object_id}", response_model=ObjectInstanceResponse)
async def get_object(object_id: str):
    results = await run_query(
        """
        MATCH (o:ObjectInstance {id: $id})
        OPTIONAL MATCH (t:ObjectType {id: o.type_id})
        RETURN o, t.name AS type_name
        """,
        {"id": object_id},
    )
    if not results:
        raise HTTPException(status_code=404, detail="Object not found")

    r = results[0]
    return ObjectInstanceResponse(
        id=r["o"]["id"],
        type_id=r["o"]["type_id"],
        type_name=r.get("type_name", ""),
        properties=r["o"].get("properties", {}),
        source_dataset=r["o"].get("source_dataset", ""),
        created_at=str(r["o"].get("created_at", "")),
    )


@router.post("")
async def create_object(body: dict):
    obj_id = str(uuid.uuid4())
    type_id = body.get("type_id", "")
    properties = body.get("properties", {})
    source_dataset = body.get("source_dataset", "")

    await run_write(
        """
        CREATE (o:ObjectInstance {
            id: $id, type_id: $type_id,
            properties: $properties, source_dataset: $source_dataset,
            created_at: datetime()
        })
        """,
        {"id": obj_id, "type_id": type_id, "properties": str(properties), "source_dataset": source_dataset},
    )
    return {"id": obj_id, "type_id": type_id, "properties": properties}


@router.get("/{object_id}/neighbors")
async def get_neighbors(object_id: str):
    results = await run_query(
        """
        MATCH (o:ObjectInstance {id: $id})-[r:RELATES_TO]-(neighbor:ObjectInstance)
        OPTIONAL MATCH (t:ObjectType {id: neighbor.type_id})
        RETURN neighbor, t.name AS type_name, type(r) AS rel_type, r.link_type_id AS link_type_id
        """,
        {"id": object_id},
    )

    return [
        {
            "id": r["neighbor"]["id"],
            "type_id": r["neighbor"]["type_id"],
            "type_name": r.get("type_name", ""),
            "link_type_id": r.get("link_type_id", ""),
            "properties": r["neighbor"].get("properties", {}),
        }
        for r in results
    ]


@router.delete("/{object_id}")
async def delete_object(object_id: str):
    await run_write(
        "MATCH (o:ObjectInstance {id: $id}) DETACH DELETE o",
        {"id": object_id},
    )
    return {"status": "deleted", "id": object_id}
