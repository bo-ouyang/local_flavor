import os
from io import StringIO

from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from community.models import CommunityAuditStatus, CommunityComment, CommunityPost, CommunityPostLike
from exchange.models import ExchangeRequest, ExchangeStatus
from interactions.models import FlavorTag
from items.models import Item, ItemAuditStatus
from messaging.models import ChatMessage, Conversation, ConversationMember
from system_config.models import SystemOption
from users.models import LocalUser


class SeedDemoDataCommandTests(TestCase):
    password = "CommandTestPassword!42"
    seed_openids = [f"seed.e2e.{number:02d}" for number in range(1, 7)]

    def seed(self, *args, **kwargs):
        output = StringIO()
        call_command("seed_demo_data", *args, stdout=output, **kwargs)
        return output.getvalue()

    def test_password_is_required_when_creating_demo_accounts(self):
        with self.assertRaisesMessage(CommandError, "--password or DEMO_SEED_PASSWORD"):
            self.seed()

    def test_seed_creates_public_data_with_valid_relations(self):
        output = self.seed(password=self.password)

        seeded_users = LocalUser.objects.filter(openid__in=self.seed_openids)
        self.assertEqual(seeded_users.count(), 6)
        self.assertFalse(self.password in output)
        for number, user in enumerate(seeded_users.order_by("openid"), start=1):
            self.assertEqual(user.phone, f"1999000000{number}")
            self.assertTrue(user.is_verified)
            self.assertTrue(check_password(self.password, user.password_hash))

        seeded_items = Item.objects.filter(user__in=seeded_users)
        self.assertEqual(seeded_items.count(), 12)
        self.assertTrue(
            seeded_items.filter(
                audit_status=ItemAuditStatus.APPROVED, is_visible=True
            ).count()
            == 12
        )
        for item in seeded_items:
            self.assertTrue(SystemOption.objects.filter(type="Category", value=item.category).exists())
            self.assertTrue(SystemOption.objects.filter(type="Season", value=item.season).exists())
            self.assertTrue(SystemOption.objects.filter(type="ShelfLife", value=item.shelf_life).exists())
            self.assertTrue(SystemOption.objects.filter(type="Portability", value=item.portability).exists())
        self.assertGreaterEqual(FlavorTag.objects.filter(item__in=seeded_items).count(), 12)

        exchange_statuses = set(
            ExchangeRequest.objects.filter(requester__in=seeded_users).values_list(
                "status", flat=True
            )
        )
        self.assertEqual(exchange_statuses, {choice for choice, _ in ExchangeStatus.CHOICES})
        self.assertGreaterEqual(
            ExchangeRequest.objects.filter(
                requester__in=seeded_users, status=ExchangeStatus.COMPLETED
            ).count(),
            3,
        )

        conversation = Conversation.objects.get(context_key="seed.e2e.conversation.01")
        messages = list(conversation.messages.order_by("seq"))
        self.assertEqual([message.seq for message in messages], list(range(1, len(messages) + 1)))
        self.assertEqual(conversation.last_seq, messages[-1].seq)
        self.assertEqual(conversation.members.count(), 2)
        unread_counts = list(
            conversation.members.order_by("user__openid").values_list("unread_count", flat=True)
        )
        self.assertEqual(unread_counts, [0, 1])
        self.assertEqual(ChatMessage.objects.filter(conversation=conversation).count(), 3)
        self.assertEqual(ConversationMember.objects.filter(conversation=conversation).count(), 2)

        posts = CommunityPost.objects.filter(user__in=seeded_users)
        self.assertGreaterEqual(posts.count(), 3)
        self.assertTrue(posts.filter(audit_status=CommunityAuditStatus.APPROVED, is_visible=True).count() == posts.count())
        self.assertGreaterEqual(CommunityComment.objects.filter(post__in=posts).count(), 3)
        self.assertGreaterEqual(CommunityPostLike.objects.filter(post__in=posts).count(), 3)

    def test_second_seed_is_idempotent(self):
        self.seed(password=self.password)
        first_counts = {
            "users": LocalUser.objects.count(),
            "items": Item.objects.count(),
            "exchanges": ExchangeRequest.objects.count(),
            "conversations": Conversation.objects.count(),
            "messages": ChatMessage.objects.count(),
            "members": ConversationMember.objects.count(),
            "posts": CommunityPost.objects.count(),
            "comments": CommunityComment.objects.count(),
            "likes": CommunityPostLike.objects.count(),
            "tags": FlavorTag.objects.count(),
        }

        self.seed(password=self.password)

        self.assertEqual(
            first_counts,
            {
                "users": LocalUser.objects.count(),
                "items": Item.objects.count(),
                "exchanges": ExchangeRequest.objects.count(),
                "conversations": Conversation.objects.count(),
                "messages": ChatMessage.objects.count(),
                "members": ConversationMember.objects.count(),
                "posts": CommunityPost.objects.count(),
                "comments": CommunityComment.objects.count(),
                "likes": CommunityPostLike.objects.count(),
                "tags": FlavorTag.objects.count(),
            },
        )

    def test_password_can_be_supplied_by_environment(self):
        os.environ["DEMO_SEED_PASSWORD"] = self.password
        self.addCleanup(os.environ.pop, "DEMO_SEED_PASSWORD", None)

        self.seed()

        self.assertTrue(
            check_password(
                self.password,
                LocalUser.objects.get(openid="seed.e2e.01").password_hash,
            )
        )

    def test_reset_removes_only_seed_namespace_data(self):
        external_user = LocalUser.objects.create(openid="existing.user", phone="18880000000")
        external_item = Item.objects.create(
            user=external_user,
            title="Existing item",
            images=["https://example.test/existing.jpg"],
            category="External",
            season="External",
            shelf_life="External",
            portability="External",
            province="Existing",
            city="Existing",
            region_code="000000",
        )
        self.seed(password=self.password)

        self.seed(reset=True)

        self.assertTrue(LocalUser.objects.filter(pk=external_user.pk).exists())
        self.assertTrue(Item.objects.filter(pk=external_item.pk).exists())
        self.assertFalse(LocalUser.objects.filter(openid__in=self.seed_openids).exists())
        self.assertFalse(Item.objects.filter(user__openid__startswith="seed.e2e.").exists())
        self.assertFalse(ExchangeRequest.objects.filter(requester__openid__startswith="seed.e2e.").exists())
        self.assertFalse(CommunityPost.objects.filter(user__openid__startswith="seed.e2e.").exists())

    def test_reset_refuses_to_delete_a_nonseed_relation_that_references_seed_data(self):
        self.seed(password=self.password)
        outside_user = LocalUser.objects.create(openid="outside.user", phone="18880000001")
        seed_item = Item.objects.filter(user__openid="seed.e2e.01").order_by("id").first()
        outside_exchange = ExchangeRequest.objects.create(
            requester=outside_user,
            owner=outside_user,
            requested_item=seed_item,
            message="outside exchange",
            status=ExchangeStatus.PENDING,
        )

        with self.assertRaisesMessage(CommandError, "non-seed relation"):
            self.seed(reset=True)

        self.assertTrue(ExchangeRequest.objects.filter(pk=outside_exchange.pk).exists())
        self.assertTrue(LocalUser.objects.filter(openid="seed.e2e.01").exists())

    def test_reset_refuses_a_nonseed_item_owned_by_a_seed_user(self):
        self.seed(password=self.password)
        seed_user = LocalUser.objects.get(openid="seed.e2e.01")
        outside_item = Item.objects.create(
            user=seed_user,
            title="outside item",
            images=["https://example.test/outside.jpg"],
            category="Snack",
            season="AllYear",
            shelf_life="Long_Months",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
        )

        with self.assertRaisesMessage(CommandError, "non-seed relation"):
            self.seed(reset=True)

        self.assertTrue(Item.objects.filter(pk=outside_item.pk).exists())
        self.assertTrue(LocalUser.objects.filter(pk=seed_user.pk).exists())

    def test_reset_refuses_a_seed_user_vote_on_an_external_tag(self):
        self.seed(password=self.password)
        seed_user = LocalUser.objects.get(openid="seed.e2e.01")
        outside_user = LocalUser.objects.create(openid="outside.user", phone="18880000002")
        outside_item = Item.objects.create(
            user=outside_user,
            title="outside item",
            images=["https://example.test/outside.jpg"],
            category="Snack",
            season="AllYear",
            shelf_life="Long_Months",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
        )
        external_tag = FlavorTag.objects.create(item=outside_item, tag_name="outside tag")
        vote = external_tag.user_votes.create(user=seed_user)

        with self.assertRaisesMessage(CommandError, "non-seed relation"):
            self.seed(reset=True)

        self.assertTrue(external_tag.user_votes.filter(pk=vote.pk).exists())
        self.assertTrue(LocalUser.objects.filter(pk=seed_user.pk).exists())

    def test_reset_refuses_an_external_exchange_with_a_seed_marker_message(self):
        self.seed(password=self.password)
        outside_user = LocalUser.objects.create(openid="outside.user", phone="18880000003")
        outside_item = Item.objects.create(
            user=outside_user,
            title="outside item",
            images=["https://example.test/outside.jpg"],
            category="Snack",
            season="AllYear",
            shelf_life="Long_Months",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
        )
        outside_exchange = ExchangeRequest.objects.create(
            requester=outside_user,
            owner=outside_user,
            requested_item=outside_item,
            message="seed.e2e.exchange.collision",
            status=ExchangeStatus.PENDING,
        )

        with self.assertRaisesMessage(CommandError, "non-seed relation"):
            self.seed(reset=True)

        self.assertTrue(ExchangeRequest.objects.filter(pk=outside_exchange.pk).exists())

    def test_reset_refuses_an_external_post_with_a_seed_marker_content(self):
        self.seed(password=self.password)
        outside_user = LocalUser.objects.create(openid="outside.user", phone="18880000004")
        outside_item = Item.objects.create(
            user=outside_user,
            title="outside item",
            images=["https://example.test/outside.jpg"],
            category="Snack",
            season="AllYear",
            shelf_life="Long_Months",
            portability="Packaged",
            province="Sichuan",
            city="Chengdu",
            region_code="510100",
        )
        outside_post = CommunityPost.objects.create(
            user=outside_user,
            item=outside_item,
            content="seed.e2e.post.collision",
            images=[],
            audit_status=CommunityAuditStatus.APPROVED,
        )

        with self.assertRaisesMessage(CommandError, "non-seed relation"):
            self.seed(reset=True)

        self.assertTrue(CommunityPost.objects.filter(pk=outside_post.pk).exists())
