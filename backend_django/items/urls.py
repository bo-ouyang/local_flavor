from django.urls import path

from items.views import ItemDetailView, ItemFlavorVoteView, ItemListCreateView, ItemTodayByRegionView


urlpatterns = [
    path("", ItemListCreateView.as_view()),
    path("today-by-region", ItemTodayByRegionView.as_view()),
    path("<int:item_id>", ItemDetailView.as_view()),
    path("<int:item_id>/flavor", ItemFlavorVoteView.as_view()),
]
