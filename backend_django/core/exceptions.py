import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


logger = logging.getLogger("app.exception")


def _extract_message(data):
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, str):
            return detail
        if detail is not None:
            return str(detail)
        if data:
            first_key = next(iter(data))
            first_value = data[first_key]
            if isinstance(first_value, list) and first_value:
                return str(first_value[0])
            return str(first_value)
    if isinstance(data, list) and data:
        return str(data[0])
    return "request failed"


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", "-")

    if response is None:
        logger.exception("Unhandled exception", exc_info=exc)
        return Response(
            {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "internal server error",
                "data": None,
                "request_id": request_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    message = _extract_message(response.data)
    payload = {
        "code": response.status_code,
        "message": message,
        "data": None,
        "request_id": request_id,
    }
    if isinstance(response.data, (dict, list)):
        payload["errors"] = response.data
    response.data = payload

    if response.status_code >= 500:
        logger.error("API server error: %s", message)
    elif response.status_code >= 400:
        logger.warning("API client error: %s", message)
    return response
