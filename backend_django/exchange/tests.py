from unittest.mock import patch

from django.db import connection
from django.test import TestCase

from core.auth import issue_token
from exchange.models import ExchangeRequest, ExchangeStatus
from items.models import Item, ItemAuditStatus
from users.models import LocalUser


class ExchangeStatusUpdateViewTests(TestCase):
    def setUp(self):
        self.requester = LocalUser.objects.create(openid="exchange-requester")
        self.owner = LocalUser.objects.create(openid="exchange-owner")
        self.requested_item = Item.objects.create(
            user=self.owner,
            title="Requested item",
            category="Snack",
            season="AllYear",
            shelf_life="Long_Months",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
            audit_status=ItemAuditStatus.APPROVED,
        )
        self.exchange = ExchangeRequest.objects.create(
            requester=self.requester,
            owner=self.owner,
            requested_item=self.requested_item,
            status=ExchangeStatus.ACCEPTED,
        )

    def test_accepted_exchange_cannot_transition_back_to_pending(self):
        real_select_for_update = ExchangeRequest.objects.select_for_update

        def select_for_update_inside_transaction(*args, **kwargs):
            self.assertTrue(connection.in_atomic_block)
            return real_select_for_update(*args, **kwargs)

        with patch.object(
            ExchangeRequest.objects,
            "select_for_update",
            side_effect=select_for_update_inside_transaction,
        ) as select_for_update:
            response = self.client.put(
                f"/django/api/v1/exchange/requests/{self.exchange.id}/status",
                data={"status": ExchangeStatus.PENDING},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {issue_token(self.requester.openid)}",
            )

        self.assertEqual(response.status_code, 400)
        select_for_update.assert_called_once_with()
        self.exchange.refresh_from_db()
        self.assertEqual(self.exchange.status, ExchangeStatus.ACCEPTED)

    def test_transition_matrix_only_contains_supported_forward_transitions(self):
        from exchange.views import ALLOWED_STATUS_TRANSITIONS

        self.assertEqual(
            ALLOWED_STATUS_TRANSITIONS,
            {
                ExchangeStatus.PENDING: {
                    ExchangeStatus.ACCEPTED,
                    ExchangeStatus.REJECTED,
                    ExchangeStatus.CANCELLED,
                },
                ExchangeStatus.ACCEPTED: {ExchangeStatus.COMPLETED},
            },
        )
