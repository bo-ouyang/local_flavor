from django.urls import path

from items.views import (
    ItemDetailView,
    ItemFavoriteListView,
    ItemFavoriteView,
    ItemFlavorVoteView,
    ItemListCreateView,
    ItemTodayByRegionView,
    ItemRecommendedView,
)


urlpatterns = [
    path("", ItemListCreateView.as_view()),
    path("recommended", ItemRecommendedView.as_view()),
    path("today-by-region", ItemTodayByRegionView.as_view()),
    path("favorites", ItemFavoriteListView.as_view()),
    path("<int:item_id>/favorite", ItemFavoriteView.as_view()),
    path("<int:item_id>", ItemDetailView.as_view()),
    path("<int:item_id>/flavor", ItemFlavorVoteView.as_view()),
]
