from rest_framework import serializers

from system_config.models import SystemOption


class SystemOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemOption
        fields = ["value", "label", "type", "sort_order"]


class SystemOptionQuerySerializer(serializers.Serializer):
    type = serializers.CharField(required=False, allow_blank=True, max_length=32)
