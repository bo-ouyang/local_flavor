from django.db import models

from exchange.models import ExchangeRequest
from items.models import Item
from users.models import LocalUser


class CommunityPost(models.Model):
    user = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="community_posts"
    )
    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="community_posts"
    )
    exchange = models.ForeignKey(
        ExchangeRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="community_posts",
    )
    content = models.TextField()
    images = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "community_posts"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["item", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]


class CommunityComment(models.Model):
    post = models.ForeignKey(
        CommunityPost, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="community_comments"
    )
    content = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    depth = models.PositiveIntegerField(default=0, db_index=True)

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    root = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="descendants"
    )

    class Meta:
        db_table = "community_comments"
        indexes = [
            models.Index(fields=["post", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["parent", "created_at"]),
            models.Index(fields=["root", "created_at"]),
        ]


class CommunityPostLike(models.Model):
    post = models.ForeignKey(
        CommunityPost, on_delete=models.CASCADE, related_name="likes"
    )
    user = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="community_post_likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "community_post_likes"
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="uq_community_post_like")
        ]
        indexes = [
            models.Index(fields=["post", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]
