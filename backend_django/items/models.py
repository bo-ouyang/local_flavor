from django.db import models

from users.models import LocalUser


class ItemAuditStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]


class Item(models.Model):
    title = models.CharField(max_length=128, db_index=True)
    description = models.TextField(null=True, blank=True)
    eat_method = models.TextField(null=True, blank=True)
    images = models.JSONField(default=list)

    category = models.CharField(max_length=32)
    season = models.CharField(max_length=32)
    shelf_life = models.CharField(max_length=32)
    portability = models.CharField(max_length=32)

    province = models.CharField(max_length=64)
    city = models.CharField(max_length=64)
    region_code = models.CharField(max_length=20, db_index=True)

    is_visible = models.BooleanField(default=True, db_index=True)
    audit_status = models.CharField(
        max_length=16,
        choices=ItemAuditStatus.CHOICES,
        default=ItemAuditStatus.PENDING,
        db_index=True,
    )
    audit_reason = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(LocalUser, on_delete=models.CASCADE, related_name="items")

    class Meta:
        db_table = "items"
        indexes = [
            models.Index(fields=["category", "created_at"]),
            models.Index(fields=["season", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["region_code", "created_at"]),
            models.Index(fields=["is_visible", "audit_status", "created_at"]),
        ]
