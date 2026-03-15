import logging
import time
import uuid

from django.conf import settings
from django.http import HttpResponse

from core.logging_context import request_id_ctx


logger = logging.getLogger("app.request")


class SimpleCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "").strip()

        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if settings.CORS_ALLOW_ALL_ORIGINS and origin:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
        elif origin and origin in settings.CORS_ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"

        if "Access-Control-Allow-Origin" in response:
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, X-Requested-With, X-Request-Id"
            )
            response["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            )
            response["Access-Control-Max-Age"] = "86400"
        return response


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
