from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.views import APIView

from core.auth import get_current_user
from core.responses import api_success
from exchange.models import ExchangeRequest, ExchangeStatus
from exchange.serializers import (
    ExchangeListQuerySerializer,
    ExchangeRequestCreateSerializer,
    ExchangeRequestReadSerializer,
    ExchangeStatusUpdateSerializer,
)
from items.models import Item, ItemAuditStatus
from messaging.services import send_system_notice
from items.tasks import sync_user_preference_task


ALLOWED_STATUS_TRANSITIONS = {
    ExchangeStatus.PENDING: {
        ExchangeStatus.ACCEPTED,
        ExchangeStatus.REJECTED,
        ExchangeStatus.CANCELLED,
    },
    ExchangeStatus.ACCEPTED: {ExchangeStatus.COMPLETED},
}


def _is_first_completed_exchange(user_id: int) -> bool:
    return (
        ExchangeRequest.objects.filter(status=ExchangeStatus.COMPLETED)
        .filter(Q(requester_id=user_id) | Q(owner_id=user_id))
        .count()
        == 1
    )


class ExchangeRequestListCreateView(APIView):
    def get(self, request):
        user = get_current_user(request, required=True)
        query_serializer = ExchangeListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        role = query_serializer.validated_data["role"]

        queryset = ExchangeRequest.objects.all().order_by("-created_at")
        if role == "sent":
            queryset = queryset.filter(requester_id=user.id)
        elif role == "received":
            queryset = queryset.filter(owner_id=user.id)
        else:
            queryset = queryset.filter(Q(requester_id=user.id) | Q(owner_id=user.id))

        return api_success(data=ExchangeRequestReadSerializer(queryset, many=True).data)

    def post(self, request):
        user = get_current_user(request, required=True)
        serializer = ExchangeRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        requested_item = Item.objects.filter(id=serializer.validated_data["requested_item_id"]).first()
        if not requested_item:
            raise NotFound("Requested item not found")
        if (
            not requested_item.is_visible
            or requested_item.audit_status != ItemAuditStatus.APPROVED
        ):
            raise ValidationError({"detail": "Requested item is not available for exchange"})
        if requested_item.user_id == user.id:
            raise ValidationError({"detail": "Cannot exchange with your own item"})

        offered_item = None
        offered_item_id = serializer.validated_data.get("offered_item_id")
        if offered_item_id:
            offered_item = Item.objects.filter(id=offered_item_id).first()
            if not offered_item:
                raise NotFound("Offered item not found")
            if offered_item.user_id != user.id:
                raise PermissionDenied("Offered item must belong to requester")
            if (
                not offered_item.is_visible
                or offered_item.audit_status != ItemAuditStatus.APPROVED
            ):
                raise ValidationError({"detail": "Offered item is not available for exchange"})

        with transaction.atomic():
            exchange = ExchangeRequest.objects.create(
                requester_id=user.id,
                owner_id=requested_item.user_id,
                requested_item_id=requested_item.id,
                offered_item=offered_item,
                message=serializer.validated_data.get("message") or "",
                status=ExchangeStatus.PENDING,
            )

        return api_success(
            data=ExchangeRequestReadSerializer(exchange).data,
            message="exchange request created",
            status_code=status.HTTP_201_CREATED,
        )


class ExchangeStatusUpdateView(APIView):
    def patch(self, request, exchange_id: int):
        return self._update(request, exchange_id)

    def put(self, request, exchange_id: int):
        return self._update(request, exchange_id)

    def _update(self, request, exchange_id: int):
        user = get_current_user(request, required=True)
        serializer = ExchangeStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_status = serializer.validated_data["status"]
        requester_first_unlock = False
        owner_first_unlock = False
        item_title = ""

        with transaction.atomic():
            exchange = (
                ExchangeRequest.objects.select_for_update()
                .select_related("requested_item")
                .filter(id=exchange_id)
                .first()
            )
            if not exchange:
                raise NotFound("Exchange request not found")
            if user.id not in (exchange.requester_id, exchange.owner_id):
                raise PermissionDenied("No permission to update this exchange request")

            current_status = exchange.status
            allowed_targets = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
            if target_status not in allowed_targets:
                raise ValidationError(
                    {
                        "detail": (
                            f"Cannot change status from {current_status} "
                            f"to {target_status}"
                        )
                    }
                )

            if (
                target_status in (ExchangeStatus.ACCEPTED, ExchangeStatus.REJECTED)
                and user.id != exchange.owner_id
            ):
                raise PermissionDenied("Only item owner can accept or reject")
            if (
                target_status == ExchangeStatus.CANCELLED
                and user.id != exchange.requester_id
            ):
                raise PermissionDenied("Only requester can cancel")

            exchange.status = target_status
            exchange.save(update_fields=["status", "updated_at"])

            if target_status == ExchangeStatus.COMPLETED:
                requester_first_unlock = _is_first_completed_exchange(
                    exchange.requester_id
                )
                owner_first_unlock = _is_first_completed_exchange(exchange.owner_id)
                item_title = exchange.requested_item.title

        if target_status == ExchangeStatus.COMPLETED:
            if requester_first_unlock:
                send_system_notice(
                    exchange.requester_id,
                    f"你已完成第一笔特产交换，社区发布权限已解锁。现在可以围绕「{item_title}」发布交流动态了。",
                    exchange.requested_item_id,
                )
            if owner_first_unlock and exchange.owner_id != exchange.requester_id:
                send_system_notice(
                    exchange.owner_id,
                    f"你已完成第一笔特产交换，社区发布权限已解锁。现在可以围绕「{item_title}」发布交流动态了。",
                    exchange.requested_item_id,
                )

            # Recalculate recommendation preferences for both parties
            sync_user_preference_task.delay(exchange.requester_id)
            if exchange.requester_id != exchange.owner_id:
                sync_user_preference_task.delay(exchange.owner_id)

        return api_success(
            data=ExchangeRequestReadSerializer(exchange).data,
            message="exchange status updated",
        )
