from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
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
from interactions.models import Comment
from interactions.serializers import CommentCreateSerializer, CommentListQuerySerializer
from items.models import Item


class CommentListCreateView(APIView):
    def get(self, request, item_id: int):
        query_serializer = CommentListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        root_limit = query_serializer.validated_data["root_limit"]

        version = get_namespace_version("comments")
        cache_key = build_cache_key(
            "comments:list",
            {"item_id": item_id, "root_limit": root_limit},
            version=version,
        )
        cached = cache_get(cache_key)
        if cached is not None:
            return api_success(data=cached)

        # Determine root comments and paginate them
        root_comments_qs = (
            Comment.objects.filter(item_id=item_id, parent_id__isnull=True)
            .select_related("user")
            .order_by("created_at")
        )

        roots = list(root_comments_qs[:root_limit])
        root_ids = [c.id for c in roots]

        # Fetch all replies for identified root comments
        replies_qs = (
            Comment.objects.filter(item_id=item_id, root_id__in=root_ids)
            .select_related("user")
            .order_by("created_at")
        )
        replies = list(replies_qs)

        nodes = {}
        result_roots = []

        # Convert to dictionary for tree building.
        for c in roots + replies:
            nodes[c.id] = {
                "id": c.id,
                "content": c.content,
                "created_at": c.created_at,
                "user_id": c.user_id,
                "user": {
                    "id": c.user_id,
                    "nickname": c.user.nickname,
                    "avatar": c.user.avatar,
                },
                "user_region_snapshot": c.user_region_snapshot,
                "parent_id": c.parent_id,
                "root_id": c.root_id,
                "depth": c.depth,
                "children_count": 0,
                "replies": [],
            }

        for c in roots + replies:
            node = nodes[c.id]
            if c.parent_id and c.parent_id in nodes:
                nodes[c.parent_id]["replies"].append(node)
                nodes[c.parent_id]["children_count"] += 1
            elif not c.parent_id:
                result_roots.append(node)

        cache_set(cache_key, result_roots, timeout=settings.CACHE_TTL_COMMENTS)
        return api_success(data=result_roots)

    def post(self, request, item_id: int):
        user = get_current_user(request, required=True)
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item = Item.objects.filter(id=item_id).first()
        if not item:
            raise NotFound("Item not found")

        if user.region_code != item.region_code:
            raise PermissionDenied("Local discussion only. You are not in the item's region.")

        parent_id = serializer.validated_data.get("parent_id")
        depth = 0
        root_id = None

        if parent_id:
            parent = Comment.objects.filter(id=parent_id, item_id=item_id).first()
            if not parent:
                raise ValidationError({"parent_id": "Parent comment does not exist in this item."})
            depth = parent.depth + 1
            root_id = parent.root_id or parent.id

        max_depth = int(getattr(settings, "COMMENT_MAX_DEPTH", 8))
        if depth > max_depth:
            raise ValidationError({"detail": f"Comment depth exceeds max {max_depth}"})

        comment = Comment.objects.create(
            content=serializer.validated_data["content"],
            user_id=user.id,
            item_id=item_id,
            user_region_snapshot=user.region_code or "",
            parent_id=parent_id,
            root_id=root_id,
            depth=depth,
        )
        bump_namespace_version("comments")

        return api_success(
            data={
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at,
                "user_id": comment.user_id,
                "user": {
                    "id": user.id,
                    "nickname": user.nickname,
                    "avatar": user.avatar,
                },
                "user_region_snapshot": comment.user_region_snapshot,
                "parent_id": comment.parent_id,
                "root_id": comment.root_id,
                "depth": comment.depth,
                "children_count": 0,
                "replies": [],
            },
            message="comment created",
            status_code=status.HTTP_201_CREATED,
        )
