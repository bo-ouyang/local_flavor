from django.db import models

from exchange.models import ExchangeRequest
from items.models import Item
from users.models import LocalUser


class CommunityAuditStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]


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
    is_visible = models.BooleanField(default=True, db_index=True)
    audit_status = models.CharField(
        max_length=16,
        choices=CommunityAuditStatus.CHOICES,
        default=CommunityAuditStatus.PENDING,
        db_index=True,
    )
    audit_reason = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "community_posts"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["item", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["is_visible", "audit_status", "created_at"]),
        ]


class CommunityComment(models.Model):
    post = models.ForeignKey(
        CommunityPost, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="community_comments"
    )
    content = models.CharField(max_length=500)
    is_visible = models.BooleanField(default=True, db_index=True)
    audit_status = models.CharField(
        max_length=16,
        choices=CommunityAuditStatus.CHOICES,
        default=CommunityAuditStatus.PENDING,
        db_index=True,
    )
    audit_reason = models.CharField(max_length=255, blank=True, default="")
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
            models.Index(fields=["post", "is_visible", "audit_status", "created_at"]),
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
