from django.test import TestCase

from core.auth import issue_token
from interactions.models import Comment
from items.models import Item, ItemAuditStatus
from users.models import LocalUser


class ItemCommentVisibilityTests(TestCase):
    def setUp(self):
        self.owner = LocalUser.objects.create(
            openid="comment-owner",
            region_code="510100",
        )
        self.local_user = LocalUser.objects.create(
            openid="comment-local-user",
            region_code="510100",
        )
        self.pending_item = Item.objects.create(
            user=self.owner,
            title="Pending item",
            category="Snack",
            season="AllYear",
            shelf_life="Long_Months",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
            audit_status=ItemAuditStatus.PENDING,
        )
        Comment.objects.create(
            item=self.pending_item,
            user=self.owner,
            content="Private pre-audit comment",
            user_region_snapshot="510100",
        )

    def test_anonymous_user_cannot_read_comments_for_pending_item(self):
        response = self.client.get(
            f"/django/api/v1/comments/{self.pending_item.id}"
        )

        self.assertEqual(response.status_code, 404)

    def test_non_owner_cannot_comment_on_pending_item(self):
        response = self.client.post(
            f"/django/api/v1/comments/{self.pending_item.id}",
            data={"content": "Should not be accepted"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {issue_token(self.local_user.openid)}",
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_can_read_comments_for_own_pending_item(self):
        response = self.client.get(
            f"/django/api/v1/comments/{self.pending_item.id}",
            HTTP_AUTHORIZATION=f"Bearer {issue_token(self.owner.openid)}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)
