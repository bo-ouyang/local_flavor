from django.db import models

from items.models import Item
from users.models import LocalUser


class ExchangeStatus:
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

    CHOICES = [
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
        (CANCELLED, "Cancelled"),
        (COMPLETED, "Completed"),
    ]


class ExchangeRequest(models.Model):
    requester = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="sent_exchange_requests"
    )
    owner = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="received_exchange_requests"
    )
    requested_item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="exchange_requests_received"
    )
    offered_item = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="exchange_requests_offered",
    )
    message = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=ExchangeStatus.CHOICES, default=ExchangeStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "exchange_requests"
        indexes = [
            models.Index(fields=["requester", "created_at"]),
            models.Index(fields=["owner", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
