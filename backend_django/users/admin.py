from django.contrib import admin

from users.models import AuthSession, LocalUser, Region


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
    exclude = ("password_hash",)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "level", "parent")
    search_fields = ("code", "name")
    list_filter = ("level",)


@admin.register(AuthSession)
class AuthSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "device_label",
        "created_at",
        "last_seen_at",
        "access_expires_at",
        "refresh_expires_at",
        "revoked_at",
    )
    list_filter = ("revoked_at", "created_at")
    search_fields = ("user__openid", "user__phone", "user__nickname", "device_label")
    exclude = ("access_token_hash",)
    readonly_fields = (
        "user",
        "access_expires_at",
        "refresh_expires_at",
        "revoked_at",
        "last_seen_at",
        "device_label",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
