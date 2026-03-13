from django.urls import path

from users.views import MeView, PhoneLoginView, RegionUpdateView, WechatLoginView


urlpatterns = [
    path("wx-login", WechatLoginView.as_view()),
    path("phone-login", PhoneLoginView.as_view()),
    path("me", MeView.as_view()),
    path("region", RegionUpdateView.as_view()),
]
