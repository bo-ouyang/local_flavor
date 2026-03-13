from django.conf import settings
from rest_framework.views import APIView

from core.cache_utils import build_cache_key, cache_get, cache_set, get_namespace_version
from core.responses import api_success
from system_config.models import SystemOption
from system_config.serializers import SystemOptionQuerySerializer, SystemOptionSerializer


class SystemOptionListView(APIView):
    def get(self, request):
        query_serializer = SystemOptionQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        option_type = query_serializer.validated_data.get("type")

        version = get_namespace_version("options")
        cache_key = build_cache_key(
            "options:list",
            {"type": option_type},
            version=version,
        )
        cached = cache_get(cache_key)
        if cached is not None:
            return api_success(data=cached)

        queryset = SystemOption.objects.all().order_by("sort_order")
        if option_type:
            queryset = queryset.filter(type=option_type)
        data = SystemOptionSerializer(queryset, many=True).data
        cache_set(cache_key, data, timeout=settings.CACHE_TTL_OPTIONS)
        return api_success(data=data)
