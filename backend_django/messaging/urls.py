from django.urls import path

from messaging.views import (
    ConversationEnsureView,
    ConversationListView,
    ConversationMessagesView,
    ConversationReadAckView,
    MessageCreateView,
    MessageHistoryView,
)


urlpatterns = [
    path("conversations", ConversationListView.as_view()),
    path("conversations/ensure", ConversationEnsureView.as_view()),
    path("conversations/<int:conversation_id>/messages", ConversationMessagesView.as_view()),
    path("conversations/<int:conversation_id>/read", ConversationReadAckView.as_view()),
    path("messages", MessageCreateView.as_view()),
    path("<int:target_id>", MessageHistoryView.as_view()),
    path("", MessageCreateView.as_view()),
]
