import os

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from community.models import (
    CommunityAuditStatus,
    CommunityComment,
    CommunityPost,
    CommunityPostLike,
)
from exchange.models import ExchangeRequest, ExchangeStatus
from interactions.models import Comment, FlavorTag, FlavorVote
from items.models import Item, ItemAuditStatus
from messaging.models import ChatMessage, Conversation, ConversationMember, Message
from system_config.models import SystemOption
from users.models import LocalUser


SEED_PREFIX = "seed.e2e."
SEED_OPENIDS = [f"{SEED_PREFIX}{number:02d}" for number in range(1, 7)]

OPTION_ROWS = (
    ("Category", "Snack", "小吃", 1),
    ("Category", "Drink", "饮品", 2),
    ("Category", "Fruit", "水果", 3),
    ("Category", "Dish", "菜肴", 4),
    ("Season", "Spring", "春季", 1),
    ("Season", "Summer", "夏季", 2),
    ("Season", "Autumn", "秋季", 3),
    ("Season", "Winter", "冬季", 4),
    ("Season", "AllYear", "四季", 5),
    ("ShelfLife", "Instant", "即时", 1),
    ("ShelfLife", "Short_Days", "短保", 2),
    ("ShelfLife", "Long_Months", "长保", 3),
    ("Portability", "EatOnSpot", "堂食", 1),
    ("Portability", "Handheld", "手持", 2),
    ("Portability", "Packaged", "可包装携带", 3),
)

USER_ROWS = (
    ("19990000001", "成都试吃者", "Sichuan", "Chengdu", "510100"),
    ("19990000002", "四川交换者", "Sichuan", "Chengdu", "510100"),
    ("19990000003", "广州试吃者", "Guangdong", "Guangzhou", "440100"),
    ("19990000004", "上海交换者", "Shanghai", "Shanghai", "310100"),
    ("19990000005", "北京试吃者", "Beijing", "Beijing", "110100"),
    ("19990000006", "西安交换者", "Shaanxi", "Xi'an", "610100"),
)


class Command(BaseCommand):
    help = "Create or reset the scoped seed.e2e demo dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            help="Password for seed.e2e accounts; alternatively set DEMO_SEED_PASSWORD.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove only the scoped seed.e2e demo dataset.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            with transaction.atomic():
                self._reset_seed_data()
            self.stdout.write(self.style.SUCCESS("seed.e2e demo data removed"))
            return

        password = (options.get("password") or os.getenv("DEMO_SEED_PASSWORD") or "").strip()
        if not password:
            raise CommandError("--password or DEMO_SEED_PASSWORD is required")

        with transaction.atomic():
            users = self._seed_users(password)
            self._seed_options()
            items = self._seed_items(users)
            exchanges = self._seed_exchanges(users, items)
            self._seed_conversation(users, items)
            self._seed_community(users, items, exchanges)

        self.stdout.write(self.style.SUCCESS("seed.e2e demo data ready"))
        self.stdout.write("Seed account phones: " + ", ".join(row[0] for row in USER_ROWS))

    def _seed_users(self, password):
        password_hash = make_password(password)
        users = {}
        for index, (phone, nickname, province, city, region_code) in enumerate(USER_ROWS, start=1):
            openid = f"{SEED_PREFIX}{index:02d}"
            user, _ = LocalUser.objects.update_or_create(
                openid=openid,
                defaults={
                    "phone": phone,
                    "password_hash": password_hash,
                    "nickname": nickname,
                    "is_verified": True,
                    "province": province,
                    "city": city,
                    "region_code": region_code,
                },
            )
            users[index] = user
        return users

    def _seed_options(self):
        for option_type, value, label, sort_order in OPTION_ROWS:
            # Options are shared configuration, so never overwrite an administrator's
            # existing value and never remove them during --reset.
            SystemOption.objects.get_or_create(
                type=option_type,
                value=value,
                defaults={"label": label, "sort_order": sort_order},
            )

    def _seed_items(self, users):
        rows = (
            (1, "麻辣兔头", "Snack", "AllYear", "Short_Days", "Packaged"),
            (1, "红糖糍粑", "Snack", "AllYear", "Short_Days", "Packaged"),
            (2, "成都冰粉", "Snack", "Summer", "Instant", "EatOnSpot"),
            (2, "花椒酥", "Snack", "Autumn", "Long_Months", "Packaged"),
            (3, "荔枝干", "Fruit", "Summer", "Long_Months", "Packaged"),
            (3, "广式凉茶", "Drink", "Summer", "Short_Days", "Handheld"),
            (4, "葱油拌面", "Dish", "Autumn", "Short_Days", "Packaged"),
            (4, "桂花糕", "Snack", "Spring", "Long_Months", "Packaged"),
            (5, "驴打滚", "Snack", "Winter", "Short_Days", "Packaged"),
            (5, "山楂卷", "Fruit", "Autumn", "Long_Months", "Handheld"),
            (6, "肉夹馍", "Snack", "AllYear", "Instant", "Handheld"),
            (6, "柿饼", "Fruit", "Winter", "Long_Months", "Packaged"),
        )
        items = {}
        for item_number, (owner_number, name, category, season, shelf_life, portability) in enumerate(rows, start=1):
            owner = users[owner_number]
            title = f"{SEED_PREFIX}{owner_number:02d}.item.{item_number:02d} {name}"
            item, _ = Item.objects.update_or_create(
                user=owner,
                title=title,
                defaults={
                    "description": f"{SEED_PREFIX} 可用于演示浏览和交换的{name}。",
                    "eat_method": "按包装说明食用。",
                    "images": [f"https://images.unsplash.com/photo-1544025162-d76694265947?w=80{item_number}"],
                    "category": category,
                    "season": season,
                    "shelf_life": shelf_life,
                    "portability": portability,
                    "province": owner.province,
                    "city": owner.city,
                    "region_code": owner.region_code,
                    "is_visible": True,
                    "audit_status": ItemAuditStatus.APPROVED,
                    "audit_reason": "",
                },
            )
            FlavorTag.objects.update_or_create(
                item=item,
                tag_name=f"{SEED_PREFIX}tag.{item_number:02d}",
                defaults={"vote_count": 1},
            )
            items[item_number] = item
        return items

    def _seed_exchanges(self, users, items):
        rows = (
            (ExchangeStatus.PENDING, 1, 3, 5, 1),
            (ExchangeStatus.ACCEPTED, 2, 4, 7, 3),
            (ExchangeStatus.REJECTED, 3, 5, 9, 5),
            (ExchangeStatus.CANCELLED, 4, 6, 11, 7),
            (ExchangeStatus.COMPLETED, 1, 3, 6, 2),
            (ExchangeStatus.COMPLETED, 2, 4, 8, 4),
            (ExchangeStatus.COMPLETED, 5, 6, 12, 9),
        )
        exchanges = {}
        for number, (status, requester, owner, requested_item, offered_item) in enumerate(rows, start=1):
            marker = f"{SEED_PREFIX}exchange.{number:02d}"
            exchange, _ = ExchangeRequest.objects.update_or_create(
                message=marker,
                defaults={
                    "requester": users[requester],
                    "owner": users[owner],
                    "requested_item": items[requested_item],
                    "offered_item": items[offered_item],
                    "status": status,
                },
            )
            exchanges[number] = exchange
        return exchanges

    def _seed_conversation(self, users, items):
        low, high = users[1], users[2]
        conversation, _ = Conversation.objects.update_or_create(
            participant_low=low,
            participant_high=high,
            context_key="seed.e2e.conversation.01",
            defaults={"item": items[1]},
        )
        ConversationMember.objects.update_or_create(
            conversation=conversation,
            user=low,
            defaults={"last_read_seq": 3, "unread_count": 0},
        )
        ConversationMember.objects.update_or_create(
            conversation=conversation,
            user=high,
            defaults={"last_read_seq": 2, "unread_count": 1},
        )
        messages = ((low, items[1], "想交换这份特产吗？"), (high, items[3], "可以，我很感兴趣。"), (low, items[2], "太好了，等你确认。"))
        for seq, (sender, item, content) in enumerate(messages, start=1):
            ChatMessage.objects.update_or_create(
                sender=sender,
                client_msg_id=f"seed.e2e.chat.01.{seq}",
                defaults={
                    "conversation": conversation,
                    "item": item,
                    "seq": seq,
                    "msg_type": ChatMessage.MSG_TYPE_TEXT,
                    "content": f"{SEED_PREFIX}{content}",
                },
            )
        latest = conversation.messages.order_by("-seq").first()
        conversation.last_seq = latest.seq
        conversation.last_message_type = latest.msg_type
        conversation.last_message_preview = latest.content[:255]
        conversation.last_message_at = latest.created_at
        conversation.save(update_fields=["last_seq", "last_message_type", "last_message_preview", "last_message_at", "updated_at"])

    def _seed_community(self, users, items, exchanges):
        rows = ((1, 3, 5, "荔枝干很适合分享。"), (2, 4, 6, "葱油拌面香气十足。"), (5, 6, 7, "肉夹馍值得回购。"))
        posts = {}
        for number, (user_number, item_number, exchange_number, content) in enumerate(rows, start=1):
            marker = f"{SEED_PREFIX}post.{number:02d}"
            post, _ = CommunityPost.objects.update_or_create(
                user=users[user_number],
                content=marker,
                defaults={
                    "item": items[item_number],
                    "exchange": exchanges[exchange_number],
                    "images": ["https://images.unsplash.com/photo-1519996529931-28324d5a630e?w=900"],
                    "is_visible": True,
                    "audit_status": CommunityAuditStatus.APPROVED,
                    "audit_reason": "",
                },
            )
            posts[number] = post
        CommunityPostLike.objects.get_or_create(post=posts[1], user=users[2])
        CommunityPostLike.objects.get_or_create(post=posts[1], user=users[3])
        CommunityPostLike.objects.get_or_create(post=posts[2], user=users[1])

        root, _ = CommunityComment.objects.update_or_create(
            post=posts[1], user=users[2], content=f"{SEED_PREFIX}comment.01",
            defaults={"parent": None, "root": None, "depth": 0, "is_visible": True, "audit_status": CommunityAuditStatus.APPROVED, "audit_reason": ""},
        )
        reply, _ = CommunityComment.objects.update_or_create(
            post=posts[1], user=users[1], content=f"{SEED_PREFIX}comment.02",
            defaults={"parent": root, "root": root, "depth": 1, "is_visible": True, "audit_status": CommunityAuditStatus.APPROVED, "audit_reason": ""},
        )
        CommunityComment.objects.update_or_create(
            post=posts[2], user=users[4], content=f"{SEED_PREFIX}comment.03",
            defaults={"parent": None, "root": None, "depth": 0, "is_visible": True, "audit_status": CommunityAuditStatus.APPROVED, "audit_reason": ""},
        )

    def _reset_seed_data(self):
        users = LocalUser.objects.filter(openid__in=SEED_OPENIDS)
        items = Item.objects.filter(user__in=users, title__startswith=SEED_PREFIX)
        marker_exchanges = ExchangeRequest.objects.filter(
            message__startswith=f"{SEED_PREFIX}exchange."
        )
        exchanges = marker_exchanges.filter(
            requester__in=users,
            owner__in=users,
            requested_item__in=items,
            offered_item__in=items,
        )
        marker_posts = CommunityPost.objects.filter(
            content__startswith=f"{SEED_PREFIX}post."
        )
        posts = marker_posts.filter(user__in=users, item__in=items, exchange__in=exchanges)
        marker_conversations = Conversation.objects.filter(
            context_key__startswith="seed.e2e.conversation."
        )
        conversations = marker_conversations.filter(
            participant_low__in=users,
            participant_high__in=users,
            item__in=items,
        )
        marker_messages = ChatMessage.objects.filter(
            client_msg_id__startswith="seed.e2e.chat."
        )
        chat_messages = marker_messages.filter(
            sender__in=users,
            conversation__in=conversations,
            item__in=items,
        )
        marker_comments = CommunityComment.objects.filter(
            content__startswith=f"{SEED_PREFIX}comment."
        )
        comments = marker_comments.filter(post__in=posts, user__in=users)
        marker_tags = FlavorTag.objects.filter(tag_name__startswith=f"{SEED_PREFIX}tag.")
        tags = marker_tags.filter(item__in=items)
        likes = CommunityPostLike.objects.filter(post__in=posts, user__in=users)

        self._assert_reset_is_scoped(
            users,
            items,
            exchanges,
            marker_exchanges,
            posts,
            marker_posts,
            conversations,
            marker_conversations,
            chat_messages,
            marker_messages,
            comments,
            marker_comments,
            tags,
            marker_tags,
            likes,
        )

        likes.delete()
        comments.delete()
        posts.delete()
        chat_messages.delete()
        ConversationMember.objects.filter(conversation__in=conversations, user__in=users).delete()
        conversations.delete()
        exchanges.delete()
        items.delete()
        users.delete()

    def _assert_reset_is_scoped(
        self,
        users,
        items,
        exchanges,
        marker_exchanges,
        posts,
        marker_posts,
        conversations,
        marker_conversations,
        chat_messages,
        marker_messages,
        comments,
        marker_comments,
        tags,
        marker_tags,
        likes,
    ):
        """Fail closed if deleting seed rows would cascade into outside data."""
        has_unmarked_seed_item = Item.objects.filter(user__in=users).exclude(pk__in=items).exists()
        has_marker_item_collision = Item.objects.filter(title__startswith=SEED_PREFIX).exclude(pk__in=items).exists()
        has_outside_exchange = ExchangeRequest.objects.filter(
            Q(requester__in=users)
            | Q(owner__in=users)
            | Q(requested_item__in=items)
            | Q(offered_item__in=items)
        ).exclude(pk__in=exchanges).exists()
        has_marker_exchange_collision = marker_exchanges.exclude(pk__in=exchanges).exists()
        has_outside_post = CommunityPost.objects.filter(
            Q(user__in=users) | Q(item__in=items)
        ).exclude(pk__in=posts).exists()
        has_marker_post_collision = marker_posts.exclude(pk__in=posts).exists()
        has_outside_comment = CommunityComment.objects.filter(
            Q(user__in=users) | Q(post__in=posts)
        ).exclude(pk__in=comments).exists()
        has_marker_comment_collision = marker_comments.exclude(pk__in=comments).exists()
        has_outside_like = CommunityPostLike.objects.filter(
            Q(user__in=users) | Q(post__in=posts)
        ).exclude(pk__in=likes).exists()
        has_outside_conversation = Conversation.objects.filter(
            Q(participant_low__in=users) | Q(participant_high__in=users)
        ).exclude(pk__in=conversations).exists()
        has_marker_conversation_collision = marker_conversations.exclude(pk__in=conversations).exists()
        has_outside_chat_message = ChatMessage.objects.filter(
            Q(sender__in=users) | Q(conversation__in=conversations)
        ).exclude(pk__in=chat_messages).exists()
        has_marker_chat_message_collision = marker_messages.exclude(pk__in=chat_messages).exists()
        has_outside_legacy_message = Message.objects.filter(
            Q(sender__in=users) | Q(receiver__in=users)
        ).exists()
        has_outside_item_relation = (
            Comment.objects.filter(item__in=items).exists()
            or FlavorTag.objects.filter(item__in=items)
            .exclude(pk__in=tags)
            .exists()
            or FlavorVote.objects.filter(Q(user__in=users) | Q(flavor_tag__in=tags)).exists()
        )
        has_marker_tag_collision = marker_tags.exclude(pk__in=tags).exists()
        if any(
            (
                has_unmarked_seed_item,
                has_marker_item_collision,
                has_outside_exchange,
                has_marker_exchange_collision,
                has_outside_post,
                has_marker_post_collision,
                has_outside_comment,
                has_marker_comment_collision,
                has_outside_like,
                has_outside_conversation,
                has_marker_conversation_collision,
                has_outside_chat_message,
                has_marker_chat_message_collision,
                has_outside_legacy_message,
                has_outside_item_relation,
                has_marker_tag_collision,
            )
        ):
            raise CommandError(
                "reset refused: non-seed relation references seed.e2e data"
            )
