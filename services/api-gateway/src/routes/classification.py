import json
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from shared.db.postgres import get_connection
from shared.models.classification import (
    ClassificationCreate,
    ClassificationRuleCreate,
    ClassificationRuleUpdate,
)
from src.middleware.auth import get_current_user

router = APIRouter()


@router.get("/datasets/{dataset_id}")
async def get_dataset_classifications(dataset_id: str):
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT * FROM data_classifications WHERE dataset_id = $1 ORDER BY column_name",
            dataset_id,
        )
    return [dict(r) for r in rows]


@router.post("/datasets/{dataset_id}")
async def set_classification(
    dataset_id: str,
    data: ClassificationCreate,
    user: dict = Depends(get_current_user),
):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO data_classifications (dataset_id, column_name, classification, reason, classified_by, auto_detected)
            VALUES ($1, $2, $3, $4, $5, FALSE)
            ON CONFLICT (dataset_id, column_name)
            DO UPDATE SET classification = $3, reason = $4, classified_by = $5, classified_at = NOW(), auto_detected = FALSE
            RETURNING *
            """,
            dataset_id, data.column_name, data.classification.value,
            data.reason, user.get("sub", "anonymous"),
        )
    return dict(row)


@router.post("/datasets/{dataset_id}/auto-detect")
async def auto_detect_classification(dataset_id: str):
    async with get_connection() as conn:
        dataset = await conn.fetchrow("SELECT schema_info FROM datasets WHERE id = $1", dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        schema_info = dataset["schema_info"]
        if isinstance(schema_info, str):
            schema_info = json.loads(schema_info)

        columns = schema_info.get("columns", [])
        if not columns:
            return {"classified": 0}

        rules = await conn.fetch("SELECT * FROM classification_rules WHERE enabled = TRUE")

        classified = 0
        for col in columns:
            col_name = col.get("name", "")
            for rule in rules:
                if re.search(rule["pattern"], col_name):
                    await conn.execute(
                        """
                        INSERT INTO data_classifications (dataset_id, column_name, classification, reason, classified_by, auto_detected)
                        VALUES ($1, $2, $3, $4, 'system', TRUE)
                        ON CONFLICT (dataset_id, column_name) DO NOTHING
                        """,
                        dataset_id, col_name, rule["classification"],
                        f"Auto-detected by rule: {rule['name']}",
                    )
                    classified += 1
                    break

    return {"classified": classified}


@router.get("/rules")
async def list_rules():
    async with get_connection() as conn:
        rows = await conn.fetch("SELECT * FROM classification_rules ORDER BY name")
    return [dict(r) for r in rows]


@router.post("/rules", status_code=201)
async def create_rule(data: ClassificationRuleCreate):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO classification_rules (name, pattern, match_type, classification, enabled)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            data.name, data.pattern, data.match_type, data.classification.value, data.enabled,
        )
    return dict(row)


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, data: ClassificationRuleUpdate):
    async with get_connection() as conn:
        existing = await conn.fetchrow("SELECT * FROM classification_rules WHERE id = $1", rule_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Rule not found")

        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.pattern is not None:
            updates["pattern"] = data.pattern
        if data.classification is not None:
            updates["classification"] = data.classification.value
        if data.enabled is not None:
            updates["enabled"] = data.enabled

        if not updates:
            return dict(existing)

        set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
        values = list(updates.values())

        row = await conn.fetchrow(
            f"UPDATE classification_rules SET {set_clause} WHERE id = $1 RETURNING *",
            rule_id, *values,
        )
    return dict(row)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str):
    async with get_connection() as conn:
        result = await conn.execute("DELETE FROM classification_rules WHERE id = $1", rule_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Rule not found")


@router.get("/summary")
async def get_summary():
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT d.id as dataset_id, d.name as dataset_name,
                   d.schema_info,
                   COUNT(dc.id) as classified_count,
                   MAX(dc.classification) as max_classification
            FROM datasets d
            LEFT JOIN data_classifications dc ON dc.dataset_id = d.id
            GROUP BY d.id, d.name, d.schema_info
            ORDER BY d.name
            """
        )

    results = []
    for r in rows:
        schema = r["schema_info"]
        if isinstance(schema, str):
            schema = json.loads(schema)
        col_count = len(schema.get("columns", [])) if schema else 0
        results.append({
            "dataset_id": r["dataset_id"],
            "dataset_name": r["dataset_name"],
            "overall_classification": r["max_classification"],
            "column_count": col_count,
            "classified_count": r["classified_count"],
        })
    return results
