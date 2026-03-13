from django.contrib import admin

from users.models import LocalUser, Region


@admin.register(LocalUser)
class LocalUserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "openid",
        "phone",
        "nickname",
        "is_verified",
        "region_code",
        "province",
        "city",
        "created_at",
    )
    search_fields = ("openid", "phone", "nickname", "province", "city", "region_code")
    list_filter = ("is_verified", "province", "city")


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "level", "parent")
    search_fields = ("code", "name")
    list_filter = ("level",)
