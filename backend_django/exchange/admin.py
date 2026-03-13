from django.contrib import admin

from exchange.models import ExchangeRequest


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "requester_id",
        "owner_id",
        "requested_item_id",
        "offered_item_id",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("requester_id", "owner_id", "requested_item_id", "offered_item_id")
