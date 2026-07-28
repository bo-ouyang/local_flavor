from django.core.cache import cache
from django.test import TestCase

from items.models import Item, ItemAuditStatus
from users.models import LocalUser


class MapStatsViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = LocalUser.objects.create(openid="stats-user")

    def _create_item(self, title, audit_status, is_visible=True):
        return Item.objects.create(
            user=self.user,
            title=title,
            category="Snack",
            season="AllYear",
            shelf_life="Long_Months",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
            audit_status=audit_status,
            is_visible=is_visible,
        )

    def test_map_stats_only_count_public_items(self):
        self._create_item("Public", ItemAuditStatus.APPROVED)
        self._create_item("Pending", ItemAuditStatus.PENDING)
        self._create_item("Rejected", ItemAuditStatus.REJECTED)
        self._create_item("Hidden", ItemAuditStatus.APPROVED, is_visible=False)

        response = self.client.get("/django/api/v1/stats/map", {"days": 7})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [{"name": "Sichuan", "value": 1}])

