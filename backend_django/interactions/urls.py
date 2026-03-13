from django.urls import path

from interactions.views import CommentListCreateView


urlpatterns = [
    path("<int:item_id>", CommentListCreateView.as_view()),
]
