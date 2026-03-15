from django.contrib import admin

from items.models import Item, ItemAuditStatus


@admin.action(description="审核通过所选特产")
def approve_items(modeladmin, request, queryset):
    queryset.update(audit_status=ItemAuditStatus.APPROVED, audit_reason="")


@admin.action(description="驳回所选特产")
def reject_items(modeladmin, request, queryset):
    queryset.update(
        audit_status=ItemAuditStatus.REJECTED,
        audit_reason="Rejected in admin",
    )


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "publisher_name",
        "category",
        "province",
        "city",
        "audit_status",
        "is_visible",
        "created_at",
    )
    search_fields = (
        "title",
        "description",
        "eat_method",
        "province",
        "city",
        "region_code",
        "user__nickname",
        "user__phone",
    )
    list_filter = (
        "audit_status",
        "is_visible",
        "category",
        "season",
        "shelf_life",
        "portability",
        "province",
        "created_at",
    )
    readonly_fields = (
        "id",
        "publisher_summary",
        "images",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("user",)
    actions = (approve_items, reject_items)
    fieldsets = (
        ("基础信息", {"fields": ("id", "title", "user", "publisher_summary")}),
        (
            "内容详情",
            {
                "fields": (
                    "description",
                    "eat_method",
                    "images",
                )
            },
        ),
        (
            "特产属性",
            {
                "fields": (
                    "category",
                    "season",
                    "shelf_life",
                    "portability",
                )
            },
        ),
        ("地区信息", {"fields": ("province", "city", "region_code")}),
        ("审核与可见性", {"fields": ("audit_status", "audit_reason", "is_visible")}),
        ("时间", {"fields": ("created_at", "updated_at")}),
    )

    def publisher_name(self, obj):
        return obj.user.nickname or f"用户{obj.user_id}"

    publisher_name.short_description = "发布者"

    def publisher_summary(self, obj):
        nickname = obj.user.nickname or "-"
        phone = obj.user.phone or "-"
        return f"ID: {obj.user_id} | 昵称: {nickname} | 手机号: {phone}"

    publisher_summary.short_description = "发布者详情"
