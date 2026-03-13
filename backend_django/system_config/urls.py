from django.urls import path

from system_config.views import SystemOptionListView


urlpatterns = [
    path("", SystemOptionListView.as_view()),
]
