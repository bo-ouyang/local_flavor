from django.urls import path

from users.views import (
    MeView,
    PhoneLoginView,
    RegionUpdateView,
    SessionListView,
    SessionLogoutView,
    SessionRefreshView,
    SessionRevokeOthersView,
    SessionRevokeView,
    WechatLoginView,
)


urlpatterns = [
    path("wx-login", WechatLoginView.as_view()),
    path("phone-login", PhoneLoginView.as_view()),
    path("me", MeView.as_view()),
    path("region", RegionUpdateView.as_view()),
    path("session/refresh", SessionRefreshView.as_view()),
    path("session/logout", SessionLogoutView.as_view()),
    path("sessions", SessionListView.as_view()),
    path("sessions/revoke-others", SessionRevokeOthersView.as_view()),
    path("sessions/<int:session_id>/revoke", SessionRevokeView.as_view()),
]
