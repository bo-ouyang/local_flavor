from django.contrib import admin

from community.models import CommunityComment, CommunityPost, CommunityPostLike


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "item", "exchange", "created_at")
    search_fields = ("content", "user__nickname", "item__title")
    list_filter = ("created_at",)


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "depth", "created_at")
    search_fields = ("content", "user__nickname", "post__id")
    list_filter = ("depth", "created_at")


@admin.register(CommunityPostLike)
class CommunityPostLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    search_fields = ("post__id", "user__nickname")
    list_filter = ("created_at",)
