from django.db import models

from items.models import Item
from users.models import LocalUser


class Comment(models.Model):
    content = models.CharField(max_length=500)
    user_region_snapshot = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    depth = models.PositiveIntegerField(default=0, db_index=True)

    user = models.ForeignKey(LocalUser, on_delete=models.CASCADE, related_name="comments")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    root = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="descendants"
    )

    class Meta:
        db_table = "comments"
        indexes = [
            models.Index(fields=["item", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["parent", "created_at"]),
            models.Index(fields=["root", "created_at"]),
        ]


class FlavorTag(models.Model):
    tag_name = models.CharField(max_length=64)
    vote_count = models.IntegerField(default=1)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="flavor_tags")

    class Meta:
        db_table = "flavor_tags"
        constraints = [
            models.UniqueConstraint(fields=["item", "tag_name"], name="uq_item_tag_name"),
        ]
        indexes = [
            models.Index(fields=["item", "vote_count"]),
        ]


class FlavorVote(models.Model):
    user = models.ForeignKey(LocalUser, on_delete=models.CASCADE, related_name="flavor_votes")
    flavor_tag = models.ForeignKey(
        FlavorTag, on_delete=models.CASCADE, related_name="user_votes"
    )

    class Meta:
        db_table = "flavor_votes"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "flavor_tag"], name="uq_user_flavor_tag"
            )
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["flavor_tag"]),
        ]
