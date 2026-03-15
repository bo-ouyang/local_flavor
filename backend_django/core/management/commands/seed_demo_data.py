from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from community.models import CommunityComment, CommunityPost, CommunityPostLike
from exchange.models import ExchangeRequest, ExchangeStatus
from interactions.models import Comment, FlavorTag
from items.models import Item
from messaging.models import ChatMessage, Conversation, ConversationMember
from system_config.models import SystemOption
from users.models import LocalUser


class Command(BaseCommand):
    help = "Seed demo users/items/chat/exchanges for local testing"

    def add_arguments(self, parser):
        parser.add_argument("--password", default="Test@123456", help="password for demo phone users")

    def handle(self, *args, **options):
        password = options["password"]
        pwd_hash = make_password(password)

        demo_users = [
            {
                "phone": "13800000000",
                "nickname": "Demo_Alice",
                "province": "Sichuan",
                "city": "Chengdu",
                "region_code": "510100",
            },
            {
                "phone": "13800000001",
                "nickname": "Demo_Bob",
                "province": "Sichuan",
                "city": "Chengdu",
                "region_code": "510100",
            },
            {
                "phone": "13800000002",
                "nickname": "Demo_Carol",
                "province": "Guangdong",
                "city": "Guangzhou",
                "region_code": "440100",
            },
            {
                "phone": "13800000003",
                "nickname": "Demo_David",
                "province": "Shanghai",
                "city": "Shanghai",
                "region_code": "310100",
            },
        ]

        users_by_phone = {}
        for row in demo_users:
            openid = f"phone_{row['phone']}"
            user, _ = LocalUser.objects.get_or_create(
                openid=openid,
                defaults={
                    "phone": row["phone"],
                    "password_hash": pwd_hash,
                    "nickname": row["nickname"],
                    "is_verified": True,
                    "province": row["province"],
                    "city": row["city"],
                    "region_code": row["region_code"],
                },
            )
            changed = False
            for field in ("phone", "nickname", "province", "city", "region_code"):
                value = row[field]
                if getattr(user, field) != value:
                    setattr(user, field, value)
                    changed = True
            if user.password_hash != pwd_hash:
                user.password_hash = pwd_hash
                changed = True
            if not user.is_verified:
                user.is_verified = True
                changed = True
            if changed:
                user.save()
            users_by_phone[row["phone"]] = user

        options_seed = [
            ("Category", "Snack", "小吃", 1),
            ("Category", "Drink", "饮品", 2),
            ("Category", "Fruit", "水果", 3),
            ("Category", "Dish", "菜肴", 4),
            ("Season", "Spring", "春", 1),
            ("Season", "Summer", "夏", 2),
            ("Season", "Autumn", "秋", 3),
            ("Season", "Winter", "冬", 4),
            ("Season", "AllYear", "四季", 5),
            ("ShelfLife", "Instant", "即食", 1),
            ("ShelfLife", "Short_Days", "短保", 2),
            ("ShelfLife", "Long_Months", "长保", 3),
            ("Portability", "EatOnSpot", "堂食", 1),
            ("Portability", "Handheld", "手持", 2),
            ("Portability", "Packaged", "可包装携带", 3),
        ]
        for option_type, value, label, sort_order in options_seed:
            SystemOption.objects.update_or_create(
                type=option_type,
                value=value,
                defaults={"label": label, "sort_order": sort_order},
            )

        demo_items = [
            {
                "owner_phone": "13800000000",
                "title": "成都麻辣兔头",
                "description": "地道成都风味，麻辣鲜香。",
                "eat_method": "加热后食用。",
                "images": ["https://images.unsplash.com/photo-1544025162-d76694265947?w=800"],
                "category": "Snack",
                "season": "AllYear",
                "shelf_life": "Short_Days",
                "portability": "Packaged",
                "province": "Sichuan",
                "city": "Chengdu",
                "region_code": "510100",
                "tags": ["麻辣", "下酒"],
            },
            {
                "owner_phone": "13800000001",
                "title": "成都冰粉",
                "description": "夏季解暑甜品。",
                "eat_method": "冷藏后口感更佳。",
                "images": ["https://images.unsplash.com/photo-1490474418585-ba9bad8fd0ea?w=800"],
                "category": "Snack",
                "season": "Summer",
                "shelf_life": "Instant",
                "portability": "EatOnSpot",
                "province": "Sichuan",
                "city": "Chengdu",
                "region_code": "510100",
                "tags": ["清爽", "甜"],
            },
            {
                "owner_phone": "13800000002",
                "title": "广州荔枝干",
                "description": "岭南风味果干，适合交换邮寄。",
                "eat_method": "开袋即食。",
                "images": ["https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?w=800"],
                "category": "Fruit",
                "season": "Summer",
                "shelf_life": "Long_Months",
                "portability": "Packaged",
                "province": "Guangdong",
                "city": "Guangzhou",
                "region_code": "440100",
                "tags": ["果香", "甜"],
            },
            {
                "owner_phone": "13800000003",
                "title": "上海葱油拌面",
                "description": "鲜香浓郁，地方特色明显。",
                "eat_method": "开水煮面后拌匀。",
                "images": ["https://images.unsplash.com/photo-1559847844-5315695dadae?w=800"],
                "category": "Dish",
                "season": "Autumn",
                "shelf_life": "Short_Days",
                "portability": "Packaged",
                "province": "Shanghai",
                "city": "Shanghai",
                "region_code": "310100",
                "tags": ["咸香", "鲜"],
            },
        ]

        items_by_title = {}
        items_by_owner_phone = {}
        for row in demo_items:
            owner = users_by_phone[row["owner_phone"]]
            item, _ = Item.objects.get_or_create(
                user=owner,
                title=row["title"],
                defaults={
                    "description": row["description"],
                    "eat_method": row["eat_method"],
                    "images": row["images"],
                    "category": row["category"],
                    "season": row["season"],
                    "shelf_life": row["shelf_life"],
                    "portability": row["portability"],
                    "province": row["province"],
                    "city": row["city"],
                    "region_code": row["region_code"],
                },
            )
            changed = False
            for field in (
                "description",
                "eat_method",
                "images",
                "category",
                "season",
                "shelf_life",
                "portability",
                "province",
                "city",
                "region_code",
            ):
                value = row[field]
                if getattr(item, field) != value:
                    setattr(item, field, value)
                    changed = True
            if changed:
                item.save()
            items_by_title[row["title"]] = item
            items_by_owner_phone[row["owner_phone"]] = item

            for tag_name in row["tags"]:
                tag, _ = FlavorTag.objects.get_or_create(
                    item=item, tag_name=tag_name, defaults={"vote_count": 1}
                )
                if tag.vote_count < 1:
                    tag.vote_count = 1
                    tag.save(update_fields=["vote_count"])

        # Seed comments in same region (with one nested reply).
        chengdu_item = items_by_title["成都麻辣兔头"]
        bob = users_by_phone["13800000001"]
        root_comment, _ = Comment.objects.get_or_create(
            user=bob,
            item=chengdu_item,
            content="这个兔头很地道，辣度很够。",
            defaults={"user_region_snapshot": bob.region_code or "", "depth": 0},
        )
        if root_comment.root_id is not None:
            root_comment.root_id = None
            root_comment.depth = 0
            root_comment.save(update_fields=["root", "depth"])

        alice = users_by_phone["13800000000"]
        reply_exists = Comment.objects.filter(
            item=chengdu_item,
            user=alice,
            parent_id=root_comment.id,
            content="收到，欢迎交换试试。",
        ).exists()
        if not reply_exists:
            Comment.objects.create(
                user=alice,
                item=chengdu_item,
                content="收到，欢迎交换试试。",
                user_region_snapshot=alice.region_code or "",
                parent=root_comment,
                root=root_comment,
                depth=1,
            )

        # Seed chat conversation/messages.
        carol = users_by_phone["13800000002"]
        low, high = (alice, carol) if alice.id < carol.id else (carol, alice)
        conversation, _ = Conversation.objects.get_or_create(
            participant_low=low,
            participant_high=high,
            context_key=Conversation.CONTEXT_GLOBAL,
            defaults={"item": items_by_title["广州荔枝干"]},
        )
        ConversationMember.objects.get_or_create(conversation=conversation, user=alice)
        ConversationMember.objects.get_or_create(conversation=conversation, user=carol)

        if not ChatMessage.objects.filter(sender=alice, client_msg_id="seed-msg-1").exists():
            ChatMessage.objects.create(
                conversation=conversation,
                sender=alice,
                item=items_by_title["广州荔枝干"],
                seq=1,
                msg_type=ChatMessage.MSG_TYPE_TEXT,
                content="你好，荔枝干可以交换吗？",
                client_msg_id="seed-msg-1",
            )
        if not ChatMessage.objects.filter(sender=carol, client_msg_id="seed-msg-2").exists():
            next_seq = (
                ChatMessage.objects.filter(conversation=conversation)
                .order_by("-seq")
                .values_list("seq", flat=True)
                .first()
                or 0
            ) + 1
            ChatMessage.objects.create(
                conversation=conversation,
                sender=carol,
                item=items_by_title["成都麻辣兔头"],
                seq=next_seq,
                msg_type=ChatMessage.MSG_TYPE_TEXT,
                content="可以，想换成都兔头。",
                client_msg_id="seed-msg-2",
            )

        latest = (
            ChatMessage.objects.filter(conversation=conversation)
            .order_by("-seq")
            .first()
        )
        if latest:
            conversation.last_seq = latest.seq
            conversation.last_message_type = latest.msg_type
            conversation.last_message_preview = latest.content[:80]
            conversation.last_message_at = latest.created_at
            conversation.save(
                update_fields=[
                    "last_seq",
                    "last_message_type",
                    "last_message_preview",
                    "last_message_at",
                    "updated_at",
                ]
            )
            ConversationMember.objects.filter(conversation=conversation, user=alice).update(
                last_read_seq=conversation.last_seq,
                unread_count=0,
            )
            ConversationMember.objects.filter(conversation=conversation, user=carol).update(
                last_read_seq=conversation.last_seq,
                unread_count=0,
            )

        # Seed exchange requests.
        existing_pending_exchange = (
            ExchangeRequest.objects.filter(
                requester=alice,
                owner=carol,
                requested_item=items_by_title["广州荔枝干"],
                offered_item=items_by_title["成都麻辣兔头"],
                status=ExchangeStatus.PENDING,
            )
            .order_by("-id")
            .first()
        )
        if not existing_pending_exchange:
            ExchangeRequest.objects.create(
                requester=alice,
                owner=carol,
                requested_item=items_by_title["广州荔枝干"],
                offered_item=items_by_title["成都麻辣兔头"],
                message="我用兔头换荔枝干",
                status=ExchangeStatus.PENDING,
            )

        existing_accepted_exchange = (
            ExchangeRequest.objects.filter(
                requester=users_by_phone["13800000001"],
                owner=users_by_phone["13800000003"],
                requested_item=items_by_title["上海葱油拌面"],
                offered_item=items_by_title["成都冰粉"],
                status=ExchangeStatus.ACCEPTED,
            )
            .order_by("-id")
            .first()
        )
        if not existing_accepted_exchange:
            ExchangeRequest.objects.create(
                requester=users_by_phone["13800000001"],
                owner=users_by_phone["13800000003"],
                requested_item=items_by_title["上海葱油拌面"],
                offered_item=items_by_title["成都冰粉"],
                message="想交换尝尝",
                status=ExchangeStatus.ACCEPTED,
            )

        completed_exchange_1 = (
            ExchangeRequest.objects.filter(
                requester=alice,
                owner=carol,
                requested_item=items_by_owner_phone["13800000002"],
                offered_item=items_by_owner_phone["13800000000"],
                status=ExchangeStatus.COMPLETED,
            )
            .order_by("-id")
            .first()
        )
        if not completed_exchange_1:
            completed_exchange_1 = ExchangeRequest.objects.create(
                requester=alice,
                owner=carol,
                requested_item=items_by_owner_phone["13800000002"],
                offered_item=items_by_owner_phone["13800000000"],
                status=ExchangeStatus.COMPLETED,
                message="seed completed exchange 1",
            )

        completed_exchange_2 = (
            ExchangeRequest.objects.filter(
                requester=users_by_phone["13800000001"],
                owner=users_by_phone["13800000003"],
                requested_item=items_by_owner_phone["13800000003"],
                offered_item=items_by_owner_phone["13800000001"],
                status=ExchangeStatus.COMPLETED,
            )
            .order_by("-id")
            .first()
        )
        if not completed_exchange_2:
            completed_exchange_2 = ExchangeRequest.objects.create(
                requester=users_by_phone["13800000001"],
                owner=users_by_phone["13800000003"],
                requested_item=items_by_owner_phone["13800000003"],
                offered_item=items_by_owner_phone["13800000001"],
                status=ExchangeStatus.COMPLETED,
                message="seed completed exchange 2",
            )

        alice_post, _ = CommunityPost.objects.get_or_create(
            user=alice,
            item=items_by_owner_phone["13800000002"],
            exchange=completed_exchange_1,
            content="Seed demo: received lychee snacks after exchange, sweet and easy to carry.",
            defaults={
                "images": [
                    "https://images.unsplash.com/photo-1519996529931-28324d5a630e?w=900"
                ]
            },
        )
        if not alice_post.images:
            alice_post.images = [
                "https://images.unsplash.com/photo-1519996529931-28324d5a630e?w=900"
            ]
            alice_post.save(update_fields=["images"])

        carol_post, _ = CommunityPost.objects.get_or_create(
            user=carol,
            item=items_by_owner_phone["13800000000"],
            exchange=completed_exchange_1,
            content="Seed demo: the spicy rabbit head has a strong flavor and works well as a late-night snack.",
            defaults={
                "images": [
                    "https://images.unsplash.com/photo-1544025162-d76694265947?w=900"
                ]
            },
        )
        if not carol_post.images:
            carol_post.images = [
                "https://images.unsplash.com/photo-1544025162-d76694265947?w=900"
            ]
            carol_post.save(update_fields=["images"])

        david = users_by_phone["13800000003"]
        bob_post, _ = CommunityPost.objects.get_or_create(
            user=bob,
            item=items_by_owner_phone["13800000003"],
            exchange=completed_exchange_2,
            content="Seed demo: the scallion oil noodles were simple to cook and very fragrant.",
            defaults={
                "images": [
                    "https://images.unsplash.com/photo-1559847844-5315695dadae?w=900"
                ]
            },
        )
        if not bob_post.images:
            bob_post.images = [
                "https://images.unsplash.com/photo-1559847844-5315695dadae?w=900"
            ]
            bob_post.save(update_fields=["images"])

        CommunityPostLike.objects.get_or_create(post=alice_post, user=carol)
        CommunityPostLike.objects.get_or_create(post=alice_post, user=bob)
        CommunityPostLike.objects.get_or_create(post=carol_post, user=alice)
        CommunityPostLike.objects.get_or_create(post=bob_post, user=david)

        root_community_comment, _ = CommunityComment.objects.get_or_create(
            post=alice_post,
            user=carol,
            parent=None,
            content="Seed demo: did you chill it before eating?",
            defaults={"root": None, "depth": 0},
        )
        if root_community_comment.root_id is not None or root_community_comment.depth != 0:
            root_community_comment.root = None
            root_community_comment.depth = 0
            root_community_comment.save(update_fields=["root", "depth"])

        first_reply, _ = CommunityComment.objects.get_or_create(
            post=alice_post,
            user=alice,
            parent=root_community_comment,
            content="Seed demo: yes, the fruit aroma gets stronger after chilling.",
            defaults={"root": root_community_comment, "depth": 1},
        )
        if first_reply.root_id != root_community_comment.id or first_reply.depth != 1:
            first_reply.root = root_community_comment
            first_reply.depth = 1
            first_reply.save(update_fields=["root", "depth"])

        second_reply, _ = CommunityComment.objects.get_or_create(
            post=alice_post,
            user=carol,
            parent=first_reply,
            content="Seed demo: nice, I will try that next time.",
            defaults={"root": root_community_comment, "depth": 2},
        )
        if second_reply.root_id != root_community_comment.id or second_reply.depth != 2:
            second_reply.root = root_community_comment
            second_reply.depth = 2
            second_reply.save(update_fields=["root", "depth"])

        self.stdout.write(self.style.SUCCESS("demo seed completed"))
        self.stdout.write(self.style.SUCCESS("test accounts:"))
        for row in demo_users:
            self.stdout.write(
                f"  phone={row['phone']} password={password} nickname={row['nickname']}"
            )
