import uuid

from fastapi import APIRouter, HTTPException

from shared.db.neo4j_client import run_query, run_write
from shared.models.ontology import (
    ObjectTypeCreate, ObjectTypeResponse,
    PropertyTypeCreate, PropertyTypeResponse,
    DatasetMappingRequest,
)

router = APIRouter()


@router.post("", response_model=ObjectTypeResponse)
async def create_object_type(body: ObjectTypeCreate):
    type_id = str(uuid.uuid4())
    await run_write(
        """
        CREATE (t:ObjectType {
            id: $id, name: $name, description: $description,
            version: 1, created_at: datetime()
        })
        """,
        {"id": type_id, "name": body.name, "description": body.description},
    )
    return ObjectTypeResponse(
        id=type_id, name=body.name, description=body.description, version=1,
    )


@router.get("", response_model=list[ObjectTypeResponse])
async def list_object_types():
    results = await run_query(
        """
        MATCH (t:ObjectType)
        OPTIONAL MATCH (t)-[:HAS_PROPERTY]->(p:PropertyType)
        OPTIONAL MATCH (t)-[l:LINKED_VIA]->(target:ObjectType)
        RETURN t, collect(DISTINCT p) AS properties,
               collect(DISTINCT {id: l.link_type_id, name: l.name,
                       target_type_id: target.id, target_type_name: target.name,
                       cardinality: l.cardinality, description: l.description}) AS links
        """
    )
    types = []
    for r in results:
        t = r["t"]
        props = [
            PropertyTypeResponse(id=p["id"], name=p["name"], data_type=p["data_type"], required=p.get("required", False))
            for p in r["properties"] if p.get("id")
        ]
        links_list = [lk for lk in r["links"] if lk.get("id")]
        types.append(ObjectTypeResponse(
            id=t["id"], name=t["name"], description=t.get("description", ""),
            version=t.get("version", 1), properties=props, links=links_list,
            created_at=str(t.get("created_at", "")),
        ))
    return types


@router.get("/{type_id}", response_model=ObjectTypeResponse)
async def get_object_type(type_id: str):
    results = await run_query(
        """
        MATCH (t:ObjectType {id: $id})
        OPTIONAL MATCH (t)-[:HAS_PROPERTY]->(p:PropertyType)
        OPTIONAL MATCH (t)-[l:LINKED_VIA]->(target:ObjectType)
        RETURN t, collect(DISTINCT p) AS properties,
               collect(DISTINCT {id: l.link_type_id, name: l.name,
                       target_type_id: target.id, target_type_name: target.name,
                       cardinality: l.cardinality, description: l.description}) AS links
        """,
        {"id": type_id},
    )
    if not results:
        raise HTTPException(status_code=404, detail="Object type not found")

    r = results[0]
    t = r["t"]
    props = [
        PropertyTypeResponse(id=p["id"], name=p["name"], data_type=p["data_type"], required=p.get("required", False))
        for p in r["properties"] if p.get("id")
    ]
    links_list = [lk for lk in r["links"] if lk.get("id")]
    return ObjectTypeResponse(
        id=t["id"], name=t["name"], description=t.get("description", ""),
        version=t.get("version", 1), properties=props, links=links_list,
        created_at=str(t.get("created_at", "")),
    )


@router.delete("/{type_id}")
async def delete_object_type(type_id: str):
    await run_write(
        """
        MATCH (t:ObjectType {id: $id})
        OPTIONAL MATCH (t)-[:HAS_PROPERTY]->(p:PropertyType)
        DETACH DELETE t, p
        """,
        {"id": type_id},
    )
    return {"status": "deleted", "id": type_id}


@router.post("/{type_id}/properties", response_model=PropertyTypeResponse)
async def add_property(type_id: str, body: PropertyTypeCreate):
    prop_id = str(uuid.uuid4())
    await run_write(
        """
        MATCH (t:ObjectType {id: $type_id})
        CREATE (p:PropertyType {
            id: $id, name: $name, data_type: $data_type,
            required: $required, description: $description
        })
        CREATE (t)-[:HAS_PROPERTY]->(p)
        """,
        {
            "type_id": type_id, "id": prop_id, "name": body.name,
            "data_type": body.data_type, "required": body.required,
            "description": body.description,
        },
    )
    return PropertyTypeResponse(
        id=prop_id, name=body.name, data_type=body.data_type,
        required=body.required, description=body.description,
    )


@router.delete("/{type_id}/properties/{prop_id}")
async def delete_property(type_id: str, prop_id: str):
    await run_write(
        """
        MATCH (t:ObjectType {id: $type_id})-[:HAS_PROPERTY]->(p:PropertyType {id: $prop_id})
        DETACH DELETE p
        """,
        {"type_id": type_id, "prop_id": prop_id},
    )
    return {"status": "deleted", "id": prop_id}


@router.post("/{type_id}/links")
async def add_link(type_id: str, body: dict):
    from shared.models.ontology import LinkTypeCreate
    link = LinkTypeCreate(**body)
    link_id = str(uuid.uuid4())
    await run_write(
        """
        MATCH (s:ObjectType {id: $source_id})
        MATCH (t:ObjectType {id: $target_id})
        CREATE (s)-[:LINKED_VIA {
            link_type_id: $link_id, name: $name,
            cardinality: $cardinality, description: $description
        }]->(t)
        """,
        {
            "source_id": type_id, "target_id": link.target_type_id,
            "link_id": link_id, "name": link.name,
            "cardinality": link.cardinality, "description": link.description,
        },
    )
    return {"id": link_id, "name": link.name, "target_type_id": link.target_type_id}


@router.post("/{type_id}/map")
async def map_dataset_to_type(type_id: str, body: DatasetMappingRequest):
    from shared.db.postgres import get_connection
    import json

    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO ontology_type_mappings (object_type_id, dataset_id, column_mappings)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT DO NOTHING
            """,
            type_id, uuid.UUID(body.dataset_id), json.dumps(body.column_mappings),
        )

    return {
        "status": "mapped",
        "type_id": type_id,
        "dataset_id": body.dataset_id,
        "column_mappings": body.column_mappings,
    }
