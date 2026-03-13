from rest_framework import serializers


class MapStatsQuerySerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=365, required=False, default=7)
