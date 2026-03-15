from django.contrib import admin

from community.models import (
    CommunityAuditStatus,
    CommunityComment,
    CommunityPost,
    CommunityPostLike,
)
from community.tasks import notify_comment_approved, notify_post_audit_result


@admin.action(description="审核通过所选帖子")
def approve_posts(modeladmin, request, queryset):
    posts = list(queryset.select_related("item"))
    for post in posts:
        if post.audit_status != CommunityAuditStatus.APPROVED:
            post.audit_status = CommunityAuditStatus.APPROVED
            post.audit_reason = ""
            post.save(update_fields=["audit_status", "audit_reason", "updated_at"])
            notify_post_audit_result(post)


@admin.action(description="驳回所选帖子")
def reject_posts(modeladmin, request, queryset):
    posts = list(queryset.select_related("item"))
    for post in posts:
        if post.audit_status != CommunityAuditStatus.REJECTED:
            post.audit_status = CommunityAuditStatus.REJECTED
            if not post.audit_reason:
                post.audit_reason = "Rejected in admin"
            post.save(update_fields=["audit_status", "audit_reason", "updated_at"])
            notify_post_audit_result(post)


@admin.action(description="审核通过所选评论")
def approve_comments(modeladmin, request, queryset):
    comments = list(
        queryset.select_related("post", "post__item", "user", "parent", "parent__user")
    )
    for comment in comments:
        if comment.audit_status != CommunityAuditStatus.APPROVED:
            comment.audit_status = CommunityAuditStatus.APPROVED
            comment.audit_reason = ""
            comment.save(update_fields=["audit_status", "audit_reason"])
            notify_comment_approved(comment)


@admin.action(description="驳回所选评论")
def reject_comments(modeladmin, request, queryset):
    queryset.update(
        audit_status=CommunityAuditStatus.REJECTED,
        audit_reason="Rejected in admin",
    )


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "author_name",
        "item_title",
        "exchange_id",
        "audit_status",
        "is_visible",
        "created_at",
    )
    search_fields = (
        "content",
        "user__nickname",
        "user__phone",
        "item__title",
        "item__province",
        "item__city",
    )
    list_filter = ("audit_status", "is_visible", "created_at")
    readonly_fields = (
        "id",
        "author_summary",
        "item_summary",
        "exchange_summary",
        "images",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("user", "item", "exchange")
    actions = (approve_posts, reject_posts)
    fieldsets = (
        ("基础信息", {"fields": ("id", "user", "author_summary")}),
        ("关联对象", {"fields": ("item", "item_summary", "exchange", "exchange_summary")}),
        ("内容详情", {"fields": ("content", "images")}),
        ("审核与可见性", {"fields": ("audit_status", "audit_reason", "is_visible")}),
        ("时间", {"fields": ("created_at", "updated_at")}),
    )

    def author_name(self, obj):
        return obj.user.nickname or f"用户{obj.user_id}"

    author_name.short_description = "作者"

    def item_title(self, obj):
        return obj.item.title

    item_title.short_description = "特产"

    def author_summary(self, obj):
        nickname = obj.user.nickname or "-"
        phone = obj.user.phone or "-"
        return f"ID: {obj.user_id} | 昵称: {nickname} | 手机号: {phone}"

    author_summary.short_description = "作者详情"

    def item_summary(self, obj):
        return (
            f"ID: {obj.item_id} | 标题: {obj.item.title} | 地区: "
            f"{obj.item.province or '-'} {obj.item.city or '-'}"
        )

    item_summary.short_description = "特产详情"

    def exchange_summary(self, obj):
        if not obj.exchange_id:
            return "-"
        return (
            f"交换ID: {obj.exchange_id} | 请求方: {obj.exchange.requester_id} | "
            f"拥有方: {obj.exchange.owner_id} | 状态: {obj.exchange.status}"
        )

    exchange_summary.short_description = "交换详情"


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "post_id",
        "author_name",
        "depth",
        "audit_status",
        "is_visible",
        "created_at",
    )
    search_fields = ("content", "user__nickname", "user__phone", "post__id")
    list_filter = ("audit_status", "is_visible", "depth", "created_at")
    readonly_fields = ("id", "post_summary", "author_summary", "created_at")
    autocomplete_fields = ("post", "user", "parent", "root")
    actions = (approve_comments, reject_comments)
    fieldsets = (
        ("基础信息", {"fields": ("id", "post", "post_summary", "user", "author_summary")}),
        ("内容详情", {"fields": ("content", "parent", "root", "depth")}),
        ("审核与可见性", {"fields": ("audit_status", "audit_reason", "is_visible")}),
        ("时间", {"fields": ("created_at",)}),
    )

    def author_name(self, obj):
        return obj.user.nickname or f"用户{obj.user_id}"

    author_name.short_description = "评论者"

    def author_summary(self, obj):
        nickname = obj.user.nickname or "-"
        phone = obj.user.phone or "-"
        return f"ID: {obj.user_id} | 昵称: {nickname} | 手机号: {phone}"

    author_summary.short_description = "评论者详情"

    def post_summary(self, obj):
        return f"帖子ID: {obj.post_id} | 特产: {obj.post.item.title} | 作者: {obj.post.user_id}"

    post_summary.short_description = "帖子详情"


@admin.register(CommunityPostLike)
class CommunityPostLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    search_fields = ("post__id", "user__nickname")
    list_filter = ("created_at",)
