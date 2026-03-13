from django.db import models

from users.models import LocalUser


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

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(LocalUser, on_delete=models.CASCADE, related_name="items")

    class Meta:
        db_table = "items"
        indexes = [
            models.Index(fields=["category", "created_at"]),
            models.Index(fields=["season", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["region_code", "created_at"]),
        ]
