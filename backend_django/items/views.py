from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from core.auth import get_current_user
from core.cache_utils import (
    build_cache_key,
    bump_namespace_version,
    cache_get,
    cache_set,
    get_namespace_version,
)
from core.responses import api_success
from core.time_utils import get_current_season
from interactions.models import FlavorTag, FlavorVote
from items.models import Item, ItemAuditStatus
from items.serializers import (
    FlavorVotePayloadSerializer,
    ItemCreateSerializer,
    ItemListQuerySerializer,
    ItemReadSerializer,
    ItemTodayByRegionQuerySerializer,
)
from items.tasks import audit_item, sync_user_preference_task
from users.models import Region, UserPreferenceSnapshot
from items.recommendation import score_item_for_user


def _public_item_queryset():
    return Item.objects.filter(is_visible=True, audit_status=ItemAuditStatus.APPROVED)


class ItemListCreateView(APIView):
    def get(self, request):
        current_user = get_current_user(request, required=False)
        query_serializer = ItemListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        query = query_serializer.validated_data

        skip = query["skip"]
        limit = query["limit"]
        region_code = query.get("region_code")
        category = query.get("category")
        season = query.get("season")
        publisher_id = query.get("publisher_id")
        current_season_only = query.get("current_season_only", False)
        search_q = query.get("q")
        can_use_cache = not current_user

        cache_key = None
        if can_use_cache:
            version = get_namespace_version("items")
            cache_key = build_cache_key("items:list", query, version=version)
            cached = cache_get(cache_key)
            if cached is not None:
                return api_success(data=cached)

        queryset = Item.objects.select_related("user").prefetch_related("flavor_tags")
        if current_user and publisher_id and current_user.id == publisher_id:
            queryset = queryset.filter(user_id=publisher_id, is_visible=True)
        else:
            queryset = queryset.filter(
                is_visible=True, audit_status=ItemAuditStatus.APPROVED
            )
            if publisher_id:
                queryset = queryset.filter(user_id=publisher_id)
        if region_code:
            queryset = queryset.filter(region_code=region_code)
        if category:
            queryset = queryset.filter(category=category)
        if season:
            queryset = queryset.filter(season=season)
        if current_season_only:
            queryset = queryset.filter(season=get_current_season())
        if search_q:
            queryset = queryset.filter(
                Q(title__icontains=search_q)
                | Q(description__icontains=search_q)
                | Q(province__icontains=search_q)
                | Q(city__icontains=search_q)
                | Q(flavor_tags__tag_name__icontains=search_q)
            ).distinct()

        items = queryset.order_by("-created_at")[skip : skip + limit]
        data = ItemReadSerializer(items, many=True).data
        if cache_key:
            cache_set(cache_key, data, timeout=settings.CACHE_TTL_ITEMS_LIST)
        return api_success(data=data)

    def post(self, request):
        user = get_current_user(request, required=True)
        serializer = ItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = dict(serializer.validated_data)
        initial_tags = validated.pop("initial_tags", [])

        if not user.region_code or not user.province or not user.city:
            raise ValidationError({"detail": "Please set your region before publishing"})

        # Publishing region is always bound to current user region.
        validated["region_code"] = user.region_code
        validated["province"] = user.province
        validated["city"] = user.city

        with transaction.atomic():
            item = Item.objects.create(user=user, **validated)
            seen = set()
            for tag_name in initial_tags:
                clean_name = tag_name.strip()
                if not clean_name or clean_name in seen:
                    continue
                seen.add(clean_name)
                FlavorTag.objects.create(item=item, tag_name=clean_name, vote_count=1)

        audit_item.delay(item.id)
        item = (
            Item.objects.select_related("user")
            .prefetch_related("flavor_tags")
            .filter(id=item.id)
            .first()
        )
        bump_namespace_version("items")
        bump_namespace_version("item_detail")
        return api_success(
            data=ItemReadSerializer(item).data,
            message="item created, awaiting audit",
            status_code=status.HTTP_201_CREATED,
        )


class ItemRecommendedView(APIView):
    def get(self, request):
        user = get_current_user(request, required=True)
        query_serializer = ItemListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        query = query_serializer.validated_data

        skip = query["skip"]
        limit = query["limit"]
        category = query.get("category")
        search_q = query.get("q")

        # Use cache restricted to this user
        version = get_namespace_version("items")
        cache_key = build_cache_key(
            f"items:recommended:{user.id}",
            query,
            version=version,
        )
        cached = cache_get(cache_key)
        if cached is not None:
            return api_success(data=cached)

        snapshot = UserPreferenceSnapshot.objects.filter(user_id=user.id).first()
        if not snapshot:
            # Cold start fallback if no snapshot generated
            snapshot = UserPreferenceSnapshot(user_id=user.id)

        # Base query for approved visible items
        queryset = _public_item_queryset().select_related("user").prefetch_related("flavor_tags")
        
        if category:
            queryset = queryset.filter(category=category)
        if search_q:
            queryset = queryset.filter(
                Q(title__icontains=search_q)
                | Q(description__icontains=search_q)
                | Q(province__icontains=search_q)
                | Q(city__icontains=search_q)
                | Q(flavor_tags__tag_name__icontains=search_q)
            ).distinct()

        # We need to fetch items to score them. To prevent pulling the whole DB, 
        # we pull a larger reasonable pool (e.g. 200 recent items) and score those.
        # In a real system you'd use a dedicated matching engine or vector DB here.
        candidate_items = list(queryset.order_by("-created_at")[:200])
        
        scored_items = []
        for item in candidate_items:
            # Don't recommend the user's own items
            if item.user_id == user.id:
                continue
                
            score, reason_tags = score_item_for_user(item, user, snapshot)
            scored_items.append({
                "item": item,
                "score": score,
                "reason_tags": reason_tags
            })
            
        # Sort by score desc, then fallback to created_at
        scored_items.sort(key=lambda x: (x["score"], x["item"].created_at), reverse=True)
        
        # Paginate
        page_items = scored_items[skip : skip + limit]
        
        # Serialize
        models_to_serialize = [si["item"] for si in page_items]
        serialized_data = ItemReadSerializer(models_to_serialize, many=True).data
        
        # Inject score and reason
        for i, s_item in enumerate(page_items):
            serialized_data[i]["score"] = s_item["score"]
            serialized_data[i]["reason_tags"] = s_item["reason_tags"]

        cache_set(cache_key, serialized_data, timeout=settings.CACHE_TTL_ITEMS_LIST)
        return api_success(data=serialized_data)


class ItemTodayByRegionView(APIView):
    def get(self, request):
        query_serializer = ItemTodayByRegionQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        region_limit = query_serializer.validated_data["region_limit"]
        item_limit = query_serializer.validated_data["item_limit"]

        version = get_namespace_version("items")
        cache_key = build_cache_key(
            "items:today_by_region",
            {
                "region_limit": region_limit,
                "item_limit": item_limit,
                "today": str(timezone.localdate()),
            },
            version=version,
        )
        cached = cache_get(cache_key)
        if cached is not None:
            return api_success(data=cached)

        today = timezone.localdate()
        base_qs = _public_item_queryset().filter(created_at__date=today).select_related("user")

        # Group and count by region to find the top `region_limit` regions
        top_regions = (
            base_qs.exclude(region_code="")
            .values("region_code")
            .annotate(count=Count("id"))
            .order_by("-count")[:region_limit]
        )
        region_codes = [r["region_code"] for r in top_regions]

        # Fetch region names
        region_name_map = {
            row.code: row.name
            for row in Region.objects.filter(code__in=region_codes).only("code", "name")
        }

        # Fetch limited items for each of the top regions
        data = []
        for rc in region_codes:
            region_items = base_qs.filter(region_code=rc).order_by("-created_at")[:item_limit]
            if not region_items:
                continue

            first_item = region_items[0]
            region_dict = {
                "region_code": first_item.region_code,
                "region_name": region_name_map.get(first_item.region_code)
                or first_item.city
                or first_item.province
                or "未知地区",
                "province": first_item.province,
                "city": first_item.city,
                "items": [
                    {
                        "id": it.id,
                        "title": it.title,
                        "images": it.images,
                        "category": it.category,
                        "season": it.season,
                        "created_at": it.created_at,
                        "user_id": it.user_id,
                    }
                    for it in region_items
                ],
            }
            data.append(region_dict)

        cache_set(cache_key, data, timeout=settings.CACHE_TTL_ITEMS_TODAY)
        return api_success(data=data)


class ItemDetailView(APIView):
    def get(self, request, item_id: int):
        current_user = get_current_user(request, required=False)
        cache_key = None
        if not current_user:
            version = get_namespace_version("item_detail")
            cache_key = build_cache_key(
                "items:detail",
                {"item_id": item_id},
                version=version,
            )
            cached = cache_get(cache_key)
            if cached is not None:
                return api_success(data=cached)

        item_queryset = Item.objects.select_related("user").prefetch_related("flavor_tags")
        if not current_user:
            item_queryset = item_queryset.filter(
                is_visible=True, audit_status=ItemAuditStatus.APPROVED
            )
        else:
            item_queryset = item_queryset.filter(
                Q(id=item_id, is_visible=True, audit_status=ItemAuditStatus.APPROVED)
                | Q(id=item_id, user_id=current_user.id, is_visible=True)
            )
        item = item_queryset.filter(id=item_id).first()
        if not item:
            raise NotFound("Item not found")

        voted_tag_ids = set()
        if current_user:
            voted_tag_ids = set(
                FlavorVote.objects.filter(
                    user_id=current_user.id, flavor_tag__item_id=item_id
                ).values_list("flavor_tag_id", flat=True)
            )

        data = ItemReadSerializer(item, context={"voted_tag_ids": voted_tag_ids}).data
        if cache_key:
            cache_set(cache_key, data, timeout=settings.CACHE_TTL_ITEM_DETAIL)
        return api_success(data=data)


class ItemFlavorVoteView(APIView):
    def post(self, request, item_id: int):
        user = get_current_user(request, required=True)
        payload = FlavorVotePayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        item = _public_item_queryset().filter(id=item_id).first()
        if not item:
            raise NotFound("Item not found")

        tag_name = payload.validated_data["tag_name"].strip()
        if not tag_name:
            raise ValidationError({"tag_name": "Tag name empty"})

        with transaction.atomic():
            target_tag, _ = FlavorTag.objects.get_or_create(
                item_id=item_id, tag_name=tag_name, defaults={"vote_count": 0}
            )

            existing_vote = (
                FlavorVote.objects.select_related("flavor_tag")
                .filter(user_id=user.id, flavor_tag__item_id=item_id)
                .first()
            )

            status_msg = "voted"
            is_voted = True
            if existing_vote:
                if existing_vote.flavor_tag_id == target_tag.id:
                    existing_vote.delete()
                    target_tag.vote_count = max(0, target_tag.vote_count - 1)
                    target_tag.save(update_fields=["vote_count"])
                    status_msg = "unvoted"
                    is_voted = False
                else:
                    old_tag = existing_vote.flavor_tag
                    old_tag.vote_count = max(0, old_tag.vote_count - 1)
                    old_tag.save(update_fields=["vote_count"])
                    existing_vote.delete()

                    FlavorVote.objects.create(user_id=user.id, flavor_tag_id=target_tag.id)
                    target_tag.vote_count += 1
                    target_tag.save(update_fields=["vote_count"])
                    status_msg = "switched"
            else:
                FlavorVote.objects.create(user_id=user.id, flavor_tag_id=target_tag.id)
                target_tag.vote_count += 1
                target_tag.save(update_fields=["vote_count"])

        sync_user_preference_task.delay(user.id)
        bump_namespace_version("items")
        bump_namespace_version("item_detail")
        return api_success(
            data={
                "status": status_msg,
                "tag": target_tag.tag_name,
                "votes": target_tag.vote_count,
                "is_voted": is_voted,
            },
            message="flavor vote updated",
        )
