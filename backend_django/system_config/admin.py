from django.contrib import admin

from system_config.models import SystemOption


@admin.register(SystemOption)
class SystemOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "value", "label", "sort_order")
    search_fields = ("type", "value", "label")
    list_filter = ("type",)
