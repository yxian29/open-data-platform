import asyncio
import re
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from shared.db.audit_client import emit_audit_event
from shared.models.audit import AuditEvent

_METHOD_TO_ACTION = {
    "GET": "read",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}

_RESOURCE_PATTERN = re.compile(r"/api/v1/(\w+)")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        path = request.url.path
        if path == "/health" or not path.startswith("/api/"):
            return response

        match = _RESOURCE_PATTERN.match(path)
        resource_type = match.group(1) if match else "unknown"

        parts = path.rstrip("/").split("/")
        resource_id = None
        if len(parts) >= 5:
            candidate = parts[4]
            if len(candidate) > 8 and candidate != resource_type:
                resource_id = candidate

        user = getattr(request.state, "user", None) or {}
        user_id = user.get("sub", "anonymous") if isinstance(user, dict) else "anonymous"

        event = AuditEvent(
            user_id=user_id,
            action=_METHOD_TO_ACTION.get(request.method, request.method.lower()),
            resource_type=resource_type,
            resource_id=resource_id,
            details={"method": request.method, "path": path},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            status="success" if response.status_code < 400 else "failure",
            duration_ms=duration_ms,
        )

        asyncio.create_task(emit_audit_event(event))
        return response
