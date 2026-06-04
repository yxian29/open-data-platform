from shared.db.postgres import get_connection
from shared.models.audit import AuditEvent


async def emit_audit_event(event: AuditEvent) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO audit_log
                (user_id, action, resource_type, resource_id, details,
                 ip_address, user_agent, session_id, status, duration_ms)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::inet, $7, $8, $9, $10)
            """,
            event.user_id,
            event.action,
            event.resource_type,
            event.resource_id,
            __import__("json").dumps(event.details),
            event.ip_address,
            event.user_agent,
            event.session_id,
            event.status,
            event.duration_ms,
        )
