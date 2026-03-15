from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def root(_request):
    return JsonResponse(
        {
            "code": 0,
            "message": "ok",
            "data": {"message": "Welcome to Local Flavor Exchange API (Django)"},
        }
    )


urlpatterns = [
    path("", root),
    path("django/admin/", admin.site.urls),
    path("django/api/v1/", include("config.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
