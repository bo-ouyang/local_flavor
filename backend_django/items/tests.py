from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from core.auth import issue_token
from exchange.models import ExchangeRequest, ExchangeStatus
from items.models import Item, ItemAuditStatus
from items.recommendation import get_publisher_completed_counts
from system_config.models import SystemOption
from users.models import LocalUser, UserPreferenceSnapshot


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


class ItemRecommendedViewQueryTests(TestCase):
    def setUp(self):
        self.user = LocalUser.objects.create(
            openid="recommendation-user",
            region_code="510100",
            province="Sichuan",
            city="Chengdu",
        )
        UserPreferenceSnapshot.objects.create(user=self.user)
        self.owners = []
        self.items = []
        for index in range(6):
            owner = LocalUser.objects.create(openid=f"recommendation-owner-{index}")
            item = Item.objects.create(
                user=owner,
                title=f"Candidate {index}",
                category="Snack",
                season="AllYear",
                shelf_life="Long_Months",
                portability="Packaged",
                province="Province",
                city="City",
                region_code=str(100000 + index),
                audit_status=ItemAuditStatus.APPROVED,
            )
            self.owners.append(owner)
            self.items.append(item)
        cache.clear()

    def test_exchange_count_queries_do_not_grow_with_candidate_count(self):
        with CaptureQueriesContext(connection) as captured_queries:
            response = self.client.get(
                "/django/api/v1/items/recommended",
                {"limit": 6},
                HTTP_AUTHORIZATION=f"Bearer {issue_token(self.user.openid)}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 6)
        exchange_queries = [
            query["sql"]
            for query in captured_queries
            if ExchangeRequest._meta.db_table in query["sql"]
        ]
        self.assertEqual(len(exchange_queries), 2)

    def test_completed_exchange_experience_changes_score_and_visible_reason(self):
        counterparty = LocalUser.objects.create(openid="recommendation-counterparty")
        experienced_owner = self.owners[0]
        experienced_item = self.items[0]
        inexperienced_item = self.items[1]
        for _ in range(6):
            ExchangeRequest.objects.create(
                requester=counterparty,
                owner=experienced_owner,
                requested_item=experienced_item,
                status=ExchangeStatus.COMPLETED,
            )

        response = self.client.get(
            "/django/api/v1/items/recommended",
            {"limit": 6},
            HTTP_AUTHORIZATION=f"Bearer {issue_token(self.user.openid)}",
        )

        self.assertEqual(response.status_code, 200)
        recommendations = {
            item["id"]: item for item in response.json()["data"]
        }
        self.assertGreater(
            recommendations[experienced_item.id]["score"],
            recommendations[inexperienced_item.id]["score"],
        )
        self.assertIn(
            "交换经验丰富",
            recommendations[experienced_item.id]["reason_tags"],
        )
        self.assertNotIn(
            "交换经验丰富",
            recommendations[inexperienced_item.id]["reason_tags"],
        )


class PublisherCompletedCountsTests(TestCase):
    def setUp(self):
        self.publisher = LocalUser.objects.create(openid="count-publisher")
        self.other_user = LocalUser.objects.create(openid="count-other")
        self.zero_user = LocalUser.objects.create(openid="count-zero")
        self.item = Item.objects.create(
            user=self.publisher,
            title="Count item",
            category="Snack",
            season="AllYear",
            shelf_life="Long_Months",
            portability="Packaged",
            province="Province",
            city="City",
            region_code="100000",
            audit_status=ItemAuditStatus.APPROVED,
        )
        self.other_item = Item.objects.create(
            user=self.other_user,
            title="Other count item",
            category="Snack",
            season="AllYear",
            shelf_life="Long_Months",
            portability="Packaged",
            province="Province",
            city="City",
            region_code="100001",
            audit_status=ItemAuditStatus.APPROVED,
        )

    def _create_exchange(self, requester, owner, requested_item, status):
        return ExchangeRequest.objects.create(
            requester=requester,
            owner=owner,
            requested_item=requested_item,
            status=status,
        )

    def test_empty_input_executes_no_queries(self):
        with CaptureQueriesContext(connection) as captured_queries:
            counts = get_publisher_completed_counts([])

        self.assertEqual(counts, {})
        self.assertEqual(len(captured_queries), 0)

    def test_counts_completed_exchange_once_per_participant(self):
        self._create_exchange(
            self.publisher,
            self.other_user,
            self.other_item,
            ExchangeStatus.COMPLETED,
        )
        self._create_exchange(
            self.other_user,
            self.publisher,
            self.item,
            ExchangeStatus.COMPLETED,
        )
        self._create_exchange(
            self.publisher,
            self.other_user,
            self.other_item,
            ExchangeStatus.PENDING,
        )
        # Historical/admin-imported anomaly: a self-exchange must count only once.
        self._create_exchange(
            self.publisher,
            self.publisher,
            self.item,
            ExchangeStatus.COMPLETED,
        )

        with CaptureQueriesContext(connection) as captured_queries:
            counts = get_publisher_completed_counts(
                [
                    self.publisher.id,
                    self.other_user.id,
                    self.publisher.id,
                    self.zero_user.id,
                ]
            )

        self.assertEqual(len(captured_queries), 2)
        self.assertEqual(
            counts,
            {
                self.publisher.id: 3,
                self.other_user.id: 2,
                self.zero_user.id: 0,
            },
        )
