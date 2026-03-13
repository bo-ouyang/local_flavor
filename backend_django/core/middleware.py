import logging
import time
import uuid

from core.logging_context import request_id_ctx


logger = logging.getLogger("app.request")


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(request_id)
        request.request_id = request_id
        start = time.perf_counter()
        try:
            response = self.get_response(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response["X-Request-Id"] = request_id
            logger.info(
                "%s %s %s %sms",
                request.method,
                request.path,
                getattr(response, "status_code", 0),
                duration_ms,
            )
            return response
        finally:
            request_id_ctx.reset(token)
