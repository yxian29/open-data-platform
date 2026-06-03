from fastapi import APIRouter

from shared.db.neo4j_client import run_query, run_write

router = APIRouter()


@router.post("")
async def create_relationship(body: dict):
    source_id = body.get("source_id", "")
    target_id = body.get("target_id", "")
    link_type_id = body.get("link_type_id", "")

    await run_write(
        """
        MATCH (s:ObjectInstance {id: $source_id})
        MATCH (t:ObjectInstance {id: $target_id})
        CREATE (s)-[:RELATES_TO {link_type_id: $link_type_id, created_at: datetime()}]->(t)
        """,
        {"source_id": source_id, "target_id": target_id, "link_type_id": link_type_id},
    )
    return {"status": "created", "source_id": source_id, "target_id": target_id}


@router.delete("")
async def delete_relationship(source_id: str, target_id: str, link_type_id: str = ""):
    if link_type_id:
        await run_write(
            """
            MATCH (s:ObjectInstance {id: $source_id})-[r:RELATES_TO {link_type_id: $link_type_id}]->(t:ObjectInstance {id: $target_id})
            DELETE r
            """,
            {"source_id": source_id, "target_id": target_id, "link_type_id": link_type_id},
        )
    else:
        await run_write(
            """
            MATCH (s:ObjectInstance {id: $source_id})-[r:RELATES_TO]->(t:ObjectInstance {id: $target_id})
            DELETE r
            """,
            {"source_id": source_id, "target_id": target_id},
        )
    return {"status": "deleted"}
