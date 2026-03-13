from django.urls import path

from exchange.views import ExchangeRequestListCreateView, ExchangeStatusUpdateView


urlpatterns = [
    path("requests", ExchangeRequestListCreateView.as_view()),
    path("requests/<int:exchange_id>/status", ExchangeStatusUpdateView.as_view()),
]
