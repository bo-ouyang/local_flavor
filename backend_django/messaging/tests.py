from django.test import SimpleTestCase

from messaging.models import ChatMessage
from messaging.serializers import MessageCreateSerializer


class MessageCreateSerializerTests(SimpleTestCase):
    def test_client_cannot_create_system_message(self):
        serializer = MessageCreateSerializer(
            data={
                "receiver_id": 2,
                "msg_type": ChatMessage.MSG_TYPE_SYSTEM,
                "content": "Forged system notice",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("msg_type", serializer.errors)

