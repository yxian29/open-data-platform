from fastapi import APIRouter, HTTPException

from shared.db.postgres import get_connection
from shared.models.audit import RetentionPolicy, RetentionPolicyUpdate

router = APIRouter()


@router.get("")
async def list_policies():
    async with get_connection() as conn:
        rows = await conn.fetch("SELECT * FROM audit_retention_policies ORDER BY resource_type")
    return [dict(r) for r in rows]


@router.put("/{policy_id}")
async def update_policy(policy_id: str, update: RetentionPolicyUpdate):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            UPDATE audit_retention_policies
            SET retention_days = $1
            WHERE id = $2
            RETURNING *
            """,
            update.retention_days, policy_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Policy not found")
    return dict(row)


@router.post("/purge")
async def purge_old_events():
    async with get_connection() as conn:
        policies = await conn.fetch("SELECT * FROM audit_retention_policies")
        total_deleted = 0
        for policy in policies:
            result = await conn.execute(
                """
                DELETE FROM audit_log
                WHERE resource_type = $1
                  AND created_at < NOW() - ($2 || ' days')::interval
                """,
                policy["resource_type"], str(policy["retention_days"]),
            )
            count = int(result.split()[-1]) if result else 0
            total_deleted += count

    return {"deleted": total_deleted}
