from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from core.auth import create_auth_session, issue_token
from exchange.models import ExchangeRequest, ExchangeStatus
from items.models import Item, ItemAuditStatus, ItemFavorite
from items.recommendation import get_publisher_completed_counts
from system_config.models import SystemOption
from users.models import LocalUser, UserPreferenceSnapshot


class FavoriteAndProfileStatsApiTests(TestCase):
    def setUp(self):
        self.user = LocalUser.objects.create(openid="favorite-user")
        self.owner = LocalUser.objects.create(openid="favorite-owner")
        self.item = Item.objects.create(
            user=self.owner,
            title="Favoriteable local snack",
            images=["https://example.com/snack.jpg"],
            category="Snack",
            season="AllYear",
            shelf_life="Short_Days",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
            audit_status=ItemAuditStatus.APPROVED,
        )
        self.credentials = create_auth_session(self.user)

    def _auth(self):
        return {"HTTP_AUTHORIZATION": f"Bearer {self.credentials.access_token}"}

    def test_favorite_target_state_endpoints_are_idempotent(self):
        first_add = self.client.put(
            f"/django/api/v1/items/{self.item.id}/favorite",
            content_type="application/json",
            **self._auth(),
        )

        self.assertEqual(first_add.status_code, 200)
        self.assertEqual(
            first_add.json()["data"],
            {"item_id": self.item.id, "is_favorite": True},
        )
        repeated_add = self.client.put(
            f"/django/api/v1/items/{self.item.id}/favorite",
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(repeated_add.status_code, 200)
        self.assertTrue(repeated_add.json()["data"]["is_favorite"])
        self.assertEqual(ItemFavorite.objects.filter(user=self.user, item=self.item).count(), 1)

        first_remove = self.client.delete(
            f"/django/api/v1/items/{self.item.id}/favorite", **self._auth()
        )
        self.assertEqual(first_remove.status_code, 200)
        self.assertFalse(first_remove.json()["data"]["is_favorite"])
        repeated_remove = self.client.delete(
            f"/django/api/v1/items/{self.item.id}/favorite", **self._auth()
        )
        self.assertEqual(repeated_remove.status_code, 200)
        self.assertFalse(repeated_remove.json()["data"]["is_favorite"])

    def test_favorites_list_is_paginated_and_only_returns_public_items(self):
        second_public_item = Item.objects.create(
            user=self.owner,
            title="Second public favorite",
            images=[],
            category="Snack",
            season="AllYear",
            shelf_life="Short_Days",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
            audit_status=ItemAuditStatus.APPROVED,
        )
        pending_item = Item.objects.create(
            user=self.owner,
            title="Pending favorite",
            images=[],
            category="Snack",
            season="AllYear",
            shelf_life="Short_Days",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
            audit_status=ItemAuditStatus.PENDING,
        )
        ItemFavorite.objects.create(user=self.user, item=self.item)
        ItemFavorite.objects.create(user=self.user, item=second_public_item)
        ItemFavorite.objects.create(user=self.user, item=pending_item)

        favorites = self.client.get(
            "/django/api/v1/items/favorites",
            {"skip": 0, "limit": 1},
            **self._auth(),
        )
        self.assertEqual(favorites.status_code, 200)
        self.assertEqual(len(favorites.json()["data"]["items"]), 1)
        self.assertTrue(favorites.json()["data"]["has_more"])
        self.assertEqual(favorites.json()["data"]["next_skip"], 1)

        next_page = self.client.get(
            "/django/api/v1/items/favorites",
            {"skip": 1, "limit": 1},
            **self._auth(),
        )
        self.assertEqual(next_page.status_code, 200)
        self.assertEqual(len(next_page.json()["data"]["items"]), 1)
        self.assertFalse(next_page.json()["data"]["has_more"])
        returned_ids = {
            row["id"] for row in favorites.json()["data"]["items"]
        } | {row["id"] for row in next_page.json()["data"]["items"]}
        self.assertEqual(returned_ids, {self.item.id, second_public_item.id})

    def test_current_user_stats_are_derived_from_persisted_records(self):
        own_item = Item.objects.create(
            user=self.user,
            title="My published snack",
            images=["https://example.com/my-snack.jpg"],
            category="Snack",
            season="AllYear",
            shelf_life="Short_Days",
            portability="Packaged",
            province="Guangdong",
            city="Guangzhou",
            region_code="440100",
            audit_status=ItemAuditStatus.PENDING,
        )
        ExchangeRequest.objects.create(
            requester=self.user,
            owner=self.owner,
            requested_item=self.item,
            status=ExchangeStatus.COMPLETED,
        )
        ExchangeRequest.objects.create(
            requester=self.owner,
            owner=self.user,
            requested_item=own_item,
            status=ExchangeStatus.ACCEPTED,
        )
        hidden_item = Item.objects.create(
            user=self.owner,
            title="Hidden favorite",
            images=[],
            category="Snack",
            season="AllYear",
            shelf_life="Short_Days",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
            audit_status=ItemAuditStatus.APPROVED,
            is_visible=False,
        )
        ItemFavorite.objects.create(user=self.user, item=self.item)
        ItemFavorite.objects.create(user=self.user, item=hidden_item)

        response = self.client.get("/django/api/v1/user/stats", **self._auth())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"],
            {
                "completed_exchange_count": 1,
                "published_item_count": 1,
                "favorite_item_count": 1,
            },
        )


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
