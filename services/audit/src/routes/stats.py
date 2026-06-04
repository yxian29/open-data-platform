from fastapi import APIRouter

from shared.db.postgres import get_connection

router = APIRouter()


@router.get("")
async def get_stats(days: int = 7):
    async with get_connection() as conn:
        total = await conn.fetchrow(
            "SELECT COUNT(*) as total FROM audit_log WHERE created_at >= NOW() - ($1 || ' days')::interval",
            str(days),
        )
        by_action = await conn.fetch(
            """
            SELECT action, COUNT(*) as count FROM audit_log
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            GROUP BY action ORDER BY count DESC
            """,
            str(days),
        )
        by_resource = await conn.fetch(
            """
            SELECT resource_type, COUNT(*) as count FROM audit_log
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            GROUP BY resource_type ORDER BY count DESC
            """,
            str(days),
        )
        by_user = await conn.fetch(
            """
            SELECT user_id, COUNT(*) as count FROM audit_log
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            GROUP BY user_id ORDER BY count DESC
            LIMIT 20
            """,
            str(days),
        )

    return {
        "total_events": total["total"],
        "period_days": days,
        "by_action": {r["action"]: r["count"] for r in by_action},
        "by_resource_type": {r["resource_type"]: r["count"] for r in by_resource},
        "by_user": {r["user_id"]: r["count"] for r in by_user},
    }
