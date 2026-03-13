from django.contrib import admin

from items.models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "category",
        "season",
        "province",
        "city",
        "region_code",
        "user_id",
        "created_at",
    )
    search_fields = ("title", "description", "province", "city", "region_code")
    list_filter = ("category", "season", "shelf_life", "portability", "province")
