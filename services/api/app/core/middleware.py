import re
import time
import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger
from app.core.request_context import set_request_id

REQUEST_ID_HEADER = "x-request-id"
# Accept upstream IDs only if they look like IDs, so clients can't inject arbitrary log content.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,128}$")

log = get_logger("atu.access")


class RequestContextMiddleware:
    """Assigns a request ID, binds it to log context, echoes it in responses and logs access.

    Pure ASGI (not BaseHTTPMiddleware) so streaming responses (SSE) are not buffered.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(REQUEST_ID_HEADER.encode(), b"").decode("latin-1")
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else str(uuid.uuid7())
        set_request_id(request_id)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = scope.get("route")
            log.info(
                "request",
                method=scope["method"],
                path=scope["path"],
                route=getattr(route, "path", None),
                status=status_code,
                duration_ms=round((time.perf_counter() - start) * 1000, 1),
            )
            set_request_id(None)
