from django.urls import path

from stats.views import MapDataProxyView, MapStatsView


urlpatterns = [
    path("map", MapStatsView.as_view()),
    path("map-data", MapDataProxyView.as_view()),
]
