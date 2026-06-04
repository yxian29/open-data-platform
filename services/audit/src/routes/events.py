import json

from fastapi import APIRouter, HTTPException, Query

from shared.db.postgres import get_connection
from shared.models.audit import AuditEvent, AuditEventResponse

router = APIRouter()


def _row_to_response(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "action": row["action"],
        "resource_type": row["resource_type"],
        "resource_id": row["resource_id"],
        "details": json.loads(row["details"]) if isinstance(row["details"], str) else (row["details"] or {}),
        "ip_address": str(row["ip_address"]) if row.get("ip_address") else None,
        "user_agent": row.get("user_agent"),
        "session_id": row.get("session_id"),
        "status": row.get("status", "success"),
        "duration_ms": row.get("duration_ms"),
        "created_at": row["created_at"],
    }


@router.post("", response_model=AuditEventResponse, status_code=201)
async def create_event(event: AuditEvent):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO audit_log
                (user_id, action, resource_type, resource_id, details,
                 ip_address, user_agent, session_id, status, duration_ms)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::inet, $7, $8, $9, $10)
            RETURNING *
            """,
            event.user_id, event.action, event.resource_type, event.resource_id,
            json.dumps(event.details), event.ip_address, event.user_agent,
            event.session_id, event.status, event.duration_ms,
        )
    return _row_to_response(row)


@router.get("")
async def list_events(
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    conditions = []
    params = []
    idx = 1

    if user_id:
        conditions.append(f"user_id = ${idx}")
        params.append(user_id)
        idx += 1
    if action:
        conditions.append(f"action = ${idx}")
        params.append(action)
        idx += 1
    if resource_type:
        conditions.append(f"resource_type = ${idx}")
        params.append(resource_type)
        idx += 1
    if resource_id:
        conditions.append(f"resource_id = ${idx}")
        params.append(resource_id)
        idx += 1
    if start_date:
        conditions.append(f"created_at >= ${idx}::timestamptz")
        params.append(start_date)
        idx += 1
    if end_date:
        conditions.append(f"created_at <= ${idx}::timestamptz")
        params.append(end_date)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])

    query = f"""
        SELECT * FROM audit_log {where}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """

    async with get_connection() as conn:
        rows = await conn.fetch(query, *params)
        count_row = await conn.fetchrow(
            f"SELECT COUNT(*) as total FROM audit_log {where}",
            *params[:-2],
        )

    return {
        "events": [_row_to_response(r) for r in rows],
        "total": count_row["total"],
        "limit": limit,
        "offset": offset,
    }


@router.get("/{event_id}")
async def get_event(event_id: str):
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM audit_log WHERE id = $1", event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    return _row_to_response(row)
