from unittest.mock import patch

from django.test import TestCase

from core.auth import issue_token
from items.models import Item
from system_config.models import SystemOption
from users.models import LocalUser


class ItemListCreateViewTests(TestCase):
    def setUp(self):
        self.user = LocalUser.objects.create(
            openid="item-publisher",
            nickname="Publisher",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
        )
        for option_type, value in (
            ("Category", "Snack"),
            ("Season", "AllYear"),
            ("ShelfLife", "Short_Days"),
            ("Portability", "Packaged"),
        ):
            SystemOption.objects.create(
                type=option_type,
                value=value,
                label=value,
            )

    @patch("items.views.audit_item.delay")
    def test_post_to_item_collection_creates_pending_item(self, audit_delay):
        response = self.client.post(
            "/django/api/v1/items/",
            data={
                "title": "Test Local Snack",
                "description": "A regional snack for exchange.",
                "eat_method": "Ready to eat",
                "images": ["https://example.com/snack.jpg"],
                "category": "Snack",
                "season": "AllYear",
                "shelf_life": "Short_Days",
                "portability": "Packaged",
                "province": "Client supplied value",
                "city": "Client supplied value",
                "region_code": "client-code",
                "initial_tags": ["spicy"],
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {issue_token(self.user.openid)}",
        )

        self.assertEqual(response.status_code, 201)
        item = Item.objects.get()
        self.assertEqual(item.user_id, self.user.id)
        self.assertEqual(item.region_code, self.user.region_code)
        self.assertEqual(item.province, self.user.province)
        self.assertEqual(item.city, self.user.city)
        audit_delay.assert_called_once_with(item.id)
