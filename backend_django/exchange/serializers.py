from rest_framework import serializers

from exchange.models import ExchangeRequest


class ExchangeRequestCreateSerializer(serializers.Serializer):
    requested_item_id = serializers.IntegerField(min_value=1)
    offered_item_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    message = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ExchangeStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["pending", "accepted", "rejected", "cancelled", "completed"]
    )


class ExchangeRequestReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRequest
        fields = [
            "id",
            "requester_id",
            "owner_id",
            "requested_item_id",
            "offered_item_id",
            "message",
            "status",
            "created_at",
            "updated_at",
        ]


class ExchangeListQuerySerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=["all", "sent", "received"], required=False, default="all"
    )
