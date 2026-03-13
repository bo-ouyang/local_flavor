from typing import Optional, Set

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.views import APIView

from community.models import CommunityComment, CommunityPost, CommunityPostLike
from community.serializers import (
    CommunityCommentCreateSerializer,
    CommunityCommentListQuerySerializer,
    CommunityItemCardSerializer,
    CommunityPostCreateSerializer,
    CommunityPostListQuerySerializer,
    CommunityPostReadSerializer,
)
from core.auth import get_current_user
from core.responses import api_success
from exchange.models import ExchangeRequest, ExchangeStatus
from items.models import Item


def _completed_exchange_item_ids_for_user(user_id: int) -> Set[int]:
    rows = (
        ExchangeRequest.objects.filter(status=ExchangeStatus.COMPLETED)
        .filter(Q(requester_id=user_id) | Q(owner_id=user_id))
        .values("requested_item_id", "offered_item_id")
    )
    item_ids: Set[int] = set()
    for row in rows:
        requested = row.get("requested_item_id")
        offered = row.get("offered_item_id")
        if requested:
            item_ids.add(int(requested))
        if offered:
            item_ids.add(int(offered))
    return item_ids


def _user_participated_completed_item_exchange(user_id: int, item_id: int) -> bool:
    if not user_id or not item_id:
        return False
    return (
        ExchangeRequest.objects.filter(status=ExchangeStatus.COMPLETED)
        .filter(Q(requester_id=user_id) | Q(owner_id=user_id))
        .filter(Q(requested_item_id=item_id) | Q(offered_item_id=item_id))
        .exists()
    )


def _resolve_exchange_for_post(
    user_id: int, item_id: int, exchange_id: Optional[int]
) -> Optional[ExchangeRequest]:
    base = (
        ExchangeRequest.objects.filter(status=ExchangeStatus.COMPLETED)
        .filter(Q(requester_id=user_id) | Q(owner_id=user_id))
        .filter(Q(requested_item_id=item_id) | Q(offered_item_id=item_id))
    )

    if exchange_id:
        exchange = base.filter(id=exchange_id).first()
        if not exchange:
            raise ValidationError(
                {"exchange_id": "invalid exchange, you did not complete this item exchange"}
            )
        return exchange

    return base.order_by("-updated_at", "-id").first()


def _author_tag(post: CommunityPost) -> str:
    item_user_id = getattr(getattr(post, "item", None), "user_id", None)
    if item_user_id and post.user_id == item_user_id:
        return "特产发布者"
    return "交换参与者"


def _exchange_hint(post: CommunityPost) -> str:
    exchange = getattr(post, "exchange", None)
    if not exchange:
        return ""

    requester = getattr(exchange, "requester", None)
    owner = getattr(exchange, "owner", None)
    counterpart = None
    if requester and requester.id == post.user_id:
        counterpart = owner
    elif owner and owner.id == post.user_id:
        counterpart = requester

    counterpart_name = ""
    if counterpart:
        counterpart_name = counterpart.nickname or f"用户{counterpart.id}"
    if counterpart_name:
        return f"来自与 {counterpart_name} 的交换"
    return "来自一次已完成交换"


def _post_payload(
    post: CommunityPost,
    can_comment: bool,
    comment_count: int,
    like_count: int,
    is_liked: bool,
) -> dict:
    payload = CommunityPostReadSerializer(post).data
    payload["can_comment"] = can_comment
    payload["comment_count"] = comment_count
    payload["like_count"] = like_count
    payload["is_liked"] = is_liked
    payload["author_tag"] = _author_tag(post)
    payload["exchange_hint"] = _exchange_hint(post)
    return payload


class CommunityPostListCreateView(APIView):
    def get(self, request):
        query_serializer = CommunityPostListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        query = query_serializer.validated_data

        skip = query["skip"]
        limit = query["limit"]
        search_q = query.get("q")

        queryset = (
            CommunityPost.objects.all()
            .select_related("user", "item", "exchange", "exchange__requester", "exchange__owner")
            .annotate(comment_count=Count("comments", distinct=True))
            .annotate(like_count=Count("likes", distinct=True))
            .order_by("-created_at", "-id")
        )
        if search_q:
            queryset = queryset.filter(
                Q(content__icontains=search_q)
                | Q(item__title__icontains=search_q)
                | Q(item__province__icontains=search_q)
                | Q(item__city__icontains=search_q)
                | Q(item__flavor_tags__tag_name__icontains=search_q)
            ).distinct()

        rows = list(queryset[skip : skip + limit])

        current_user = get_current_user(request, required=False)
        allowed_item_ids: Set[int] = set()
        if current_user:
            allowed_item_ids = _completed_exchange_item_ids_for_user(current_user.id)

        liked_post_ids: Set[int] = set()
        if current_user:
            liked_post_ids = set(
                CommunityPostLike.objects.filter(
                    user_id=current_user.id, post_id__in=[row.id for row in rows]
                ).values_list("post_id", flat=True)
            )

        result = []
        for row in rows:
            result.append(
                _post_payload(
                    row,
                    can_comment=row.item_id in allowed_item_ids if current_user else False,
                    comment_count=getattr(row, "comment_count", 0),
                    like_count=getattr(row, "like_count", 0),
                    is_liked=row.id in liked_post_ids,
                )
            )
        return api_success(data=result)

    def post(self, request):
        user = get_current_user(request, required=True)
        serializer = CommunityPostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item_id = serializer.validated_data["item_id"]
        exchange_id = serializer.validated_data.get("exchange_id")

        item = Item.objects.filter(id=item_id).first()
        if not item:
            raise NotFound("Item not found")

        if not _user_participated_completed_item_exchange(user.id, item_id):
            raise PermissionDenied("Only users who completed exchange for this item can post")

        exchange = _resolve_exchange_for_post(user.id, item_id, exchange_id)
        if not exchange:
            raise ValidationError(
                {"detail": "No completed exchange record found for this item"}
            )

        post = CommunityPost.objects.create(
            user_id=user.id,
            item_id=item_id,
            exchange_id=exchange.id,
            content=serializer.validated_data["content"],
            images=serializer.validated_data.get("images") or [],
        )
        post = (
            CommunityPost.objects.select_related(
                "user", "item", "exchange", "exchange__requester", "exchange__owner"
            )
            .filter(id=post.id)
            .first()
        )
        return api_success(
            data=_post_payload(
                post,
                can_comment=True,
                comment_count=0,
                like_count=0,
                is_liked=False,
            ),
            message="community post created",
            status_code=status.HTTP_201_CREATED,
        )


class CommunityPostDetailView(APIView):
    def get(self, request, post_id: int):
        post = (
            CommunityPost.objects.select_related(
                "user", "item", "exchange", "exchange__requester", "exchange__owner"
            )
            .annotate(comment_count=Count("comments", distinct=True))
            .annotate(like_count=Count("likes", distinct=True))
            .filter(id=post_id)
            .first()
        )
        if not post:
            raise NotFound("Community post not found")

        current_user = get_current_user(request, required=False)
        can_comment = False
        is_liked = False
        if current_user:
            can_comment = _user_participated_completed_item_exchange(
                current_user.id, post.item_id
            )
            is_liked = CommunityPostLike.objects.filter(
                post_id=post.id, user_id=current_user.id
            ).exists()

        return api_success(
            data=_post_payload(
                post,
                can_comment=can_comment,
                comment_count=getattr(post, "comment_count", 0),
                like_count=getattr(post, "like_count", 0),
                is_liked=is_liked,
            )
        )


class CommunityPostCommentsView(APIView):
    def get(self, request, post_id: int):
        post = CommunityPost.objects.filter(id=post_id).only("id").first()
        if not post:
            raise NotFound("Community post not found")

        query_serializer = CommunityCommentListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        root_limit = query_serializer.validated_data["root_limit"]

        comments = (
            CommunityComment.objects.filter(post_id=post_id)
            .select_related("user")
            .order_by("created_at")
        )

        nodes = {}
        roots = []
        for c in comments:
            nodes[c.id] = {
                "id": c.id,
                "post_id": c.post_id,
                "content": c.content,
                "created_at": c.created_at,
                "user_id": c.user_id,
                "user": {
                    "id": c.user_id,
                    "nickname": c.user.nickname,
                    "avatar": c.user.avatar,
                },
                "parent_id": c.parent_id,
                "root_id": c.root_id,
                "depth": c.depth,
                "children_count": 0,
                "replies": [],
            }

        for c in comments:
            node = nodes[c.id]
            if c.parent_id and c.parent_id in nodes:
                nodes[c.parent_id]["replies"].append(node)
                nodes[c.parent_id]["children_count"] += 1
            else:
                roots.append(node)

        if len(roots) > root_limit:
            roots = roots[-root_limit:]

        return api_success(data=roots)

    def post(self, request, post_id: int):
        user = get_current_user(request, required=True)

        post = CommunityPost.objects.select_related("item").filter(id=post_id).first()
        if not post:
            raise NotFound("Community post not found")

        if not _user_participated_completed_item_exchange(user.id, post.item_id):
            raise PermissionDenied(
                "Only users who completed exchange for this item can comment"
            )

        serializer = CommunityCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        parent_id = serializer.validated_data.get("parent_id")
        depth = 0
        root_id = None

        if parent_id:
            parent = CommunityComment.objects.filter(id=parent_id, post_id=post_id).first()
            if not parent:
                raise ValidationError(
                    {"parent_id": "Parent comment does not exist in this post."}
                )
            depth = parent.depth + 1
            root_id = parent.root_id or parent.id

        max_depth = int(getattr(settings, "COMMENT_MAX_DEPTH", 8))
        if depth > max_depth:
            raise ValidationError({"detail": f"Comment depth exceeds max {max_depth}"})

        with transaction.atomic():
            comment = CommunityComment.objects.create(
                post_id=post_id,
                user_id=user.id,
                content=serializer.validated_data["content"],
                parent_id=parent_id,
                root_id=root_id,
                depth=depth,
            )

        return api_success(
            data={
                "id": comment.id,
                "post_id": comment.post_id,
                "content": comment.content,
                "created_at": comment.created_at,
                "user_id": comment.user_id,
                "user": {
                    "id": user.id,
                    "nickname": user.nickname,
                    "avatar": user.avatar,
                },
                "parent_id": comment.parent_id,
                "root_id": comment.root_id,
                "depth": comment.depth,
                "children_count": 0,
                "replies": [],
            },
            message="community comment created",
            status_code=status.HTTP_201_CREATED,
        )


class CommunityEligibleItemsView(APIView):
    def get(self, request):
        user = get_current_user(request, required=True)
        item_ids = _completed_exchange_item_ids_for_user(user.id)
        if not item_ids:
            return api_success(data=[])

        items = (
            Item.objects.filter(id__in=item_ids)
            .order_by("-created_at", "-id")
            .only(
                "id",
                "title",
                "images",
                "category",
                "province",
                "city",
                "region_code",
            )
        )
        data = CommunityItemCardSerializer(items, many=True).data
        return api_success(data=data)


class CommunityPostLikeToggleView(APIView):
    def post(self, request, post_id: int):
        user = get_current_user(request, required=True)
        post = CommunityPost.objects.filter(id=post_id).only("id").first()
        if not post:
            raise NotFound("Community post not found")

        like = CommunityPostLike.objects.filter(post_id=post_id, user_id=user.id).first()
        if like:
            like.delete()
            liked = False
        else:
            CommunityPostLike.objects.create(post_id=post_id, user_id=user.id)
            liked = True

        like_count = CommunityPostLike.objects.filter(post_id=post_id).count()
        return api_success(
            data={
                "post_id": post_id,
                "liked": liked,
                "like_count": like_count,
            },
            message="community post like updated",
        )
