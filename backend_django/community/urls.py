from django.urls import path

from community.views import (
    CommunityEligibleItemsView,
    CommunityPostDetailView,
    CommunityPostListCreateView,
    CommunityPostCommentsView,
    CommunityPostLikeToggleView,
)


urlpatterns = [
    path("posts", CommunityPostListCreateView.as_view()),
    path("posts/<int:post_id>", CommunityPostDetailView.as_view()),
    path("posts/<int:post_id>/comments", CommunityPostCommentsView.as_view()),
    path("posts/<int:post_id>/like", CommunityPostLikeToggleView.as_view()),
    path("eligible-items", CommunityEligibleItemsView.as_view()),
]
