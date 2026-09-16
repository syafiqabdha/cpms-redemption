import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logging import get_logger, set_request_id

logger = get_logger("app.middleware.access")


class RequestIDAndAccessLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Propagates or generates X-Request-ID correlation IDs.
    2. Measures request execution duration.
    3. Emits structured JSON access logs.
    4. Catches unhandled exceptions and formats standard error responses.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Resolve or generate Request ID
        incoming_req_id = request.headers.get("X-Request-ID")
        if incoming_req_id and incoming_req_id.strip():
            req_id = incoming_req_id.strip()
        else:
            req_id = str(uuid.uuid4())
        set_request_id(req_id)

        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Ensure X-Request-ID header is on response
            response.headers["X-Request-ID"] = req_id

            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} ({duration_ms}ms)",
                extra={
                    "http": {
                        "method": request.method,
                        "path": request.url.path,
                        "query": str(request.url.query) if request.url.query else None,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "client_ip": client_ip,
                        "user_agent": request.headers.get("user-agent"),
                    }
                },
            )
            return response

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                f"Unhandled exception on {request.method} {request.url.path}: {exc}",
                extra={
                    "http": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                        "client_ip": client_ip,
                        "status_code": 500,
                    }
                },
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred.",
                },
                headers={"X-Request-ID": req_id},
            )
