import json
from datetime import timedelta
from urllib.request import Request, urlopen

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from core.cache_utils import build_cache_key, cache_get, cache_set, get_namespace_version
from core.responses import api_success
from items.models import Item, ItemAuditStatus
from stats.serializers import MapStatsQuerySerializer


class MapStatsView(APIView):
    def get(self, request):
        query_serializer = MapStatsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        days = query_serializer.validated_data["days"]

        version = get_namespace_version("items")
        cache_key = build_cache_key(
            "stats:map",
            {"days": days},
            version=version,
        )
        cached = cache_get(cache_key)
        if cached is not None:
            return api_success(data=cached)

        cutoff = timezone.now() - timedelta(days=days)

        rows = (
            Item.objects.filter(
                created_at__gt=cutoff,
                is_visible=True,
                audit_status=ItemAuditStatus.APPROVED,
            )
            .values("province")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        data = [{"name": row["province"], "value": row["count"]} for row in rows]
        cache_set(cache_key, data, timeout=settings.CACHE_TTL_STATS_MAP)
        return api_success(data=data)


class MapDataUnavailable(APIException):
    status_code = 502
    default_detail = "Failed to fetch map data"
    default_code = "map_data_unavailable"


class MapDataProxyView(APIView):
    primary_url = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
    fallback_url = (
        "https://raw.githubusercontent.com/apache/echarts-examples/master/public/data/asset/geo/china.json"
    )

    def _fetch_json(self, url: str):
        req = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                )
            },
        )
        with urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get(self, _request):
        cache_key = "stats:map_data:china"
        cached = cache_get(cache_key)
        if cached is not None:
            return api_success(data=cached)
        try:
            data = self._fetch_json(self.primary_url)
            cache_set(cache_key, data, timeout=settings.CACHE_TTL_STATS_MAP_DATA)
            return api_success(data=data)
        except Exception:
            try:
                data = self._fetch_json(self.fallback_url)
                cache_set(cache_key, data, timeout=settings.CACHE_TTL_STATS_MAP_DATA)
                return api_success(data=data)
            except Exception:
                raise MapDataUnavailable()
