from django.contrib import admin

from interactions.models import Comment, FlavorTag, FlavorVote


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "item_id", "user_id", "parent_id", "root_id", "depth", "created_at","content")
    search_fields = ("content", "user_region_snapshot")
    list_filter = ("created_at", "user_region_snapshot", "depth")


@admin.register(FlavorTag)
class FlavorTagAdmin(admin.ModelAdmin):
    list_display = ("id", "item_id", "tag_name", "vote_count")
    search_fields = ("tag_name",)
    list_filter = ("item_id",)


@admin.register(FlavorVote)
class FlavorVoteAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "flavor_tag_id")
    list_filter = ("user_id", "flavor_tag_id")
