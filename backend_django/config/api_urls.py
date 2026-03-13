from django.urls import include, path


urlpatterns = [
    path("items/", include("items.urls")),
    path("exchange/", include("exchange.urls")),
    path("comments/", include("interactions.urls")),
    path("user/", include("users.urls")),
    path("chat/", include("messaging.urls")),
    path("options/", include("system_config.urls")),
    path("stats/", include("stats.urls")),
    path("upload/", include("uploads.urls")),
    path("community/", include("community.urls")),
]
