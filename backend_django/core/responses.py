from rest_framework import status
from rest_framework.response import Response


def api_success(
    data=None,
    message: str = "ok",
    code: int = 0,
    status_code: int = status.HTTP_200_OK,
):
    return Response(
        {"code": code, "message": message, "data": data},
        status=status_code,
    )
