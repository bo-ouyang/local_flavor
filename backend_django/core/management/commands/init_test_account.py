from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from users.models import LocalUser


class Command(BaseCommand):
    help = "Create or update a default test account for phone login"

    def add_arguments(self, parser):
        parser.add_argument("--phone", default="13800000000", help="test phone number")
        parser.add_argument("--password", default="Test@123456", help="test password")
        parser.add_argument("--nickname", default="TestUser", help="test nickname")

    def handle(self, *args, **options):
        phone = options["phone"]
        password = options["password"]
        nickname = options["nickname"]
        openid = f"phone_{phone}"

        user, created = LocalUser.objects.get_or_create(
            openid=openid,
            defaults={
                "phone": phone,
                "password_hash": make_password(password),
                "nickname": nickname,
                "is_verified": True,
                "province": "Sichuan",
                "city": "Chengdu",
                "region_code": "510100",
            },
        )

        if not created:
            user.phone = phone
            user.password_hash = make_password(password)
            if not user.nickname:
                user.nickname = nickname
            if not user.region_code:
                user.region_code = "510100"
            if not user.city:
                user.city = "Chengdu"
            if not user.province:
                user.province = "Sichuan"
            user.is_verified = True
            user.save()

        self.stdout.write(self.style.SUCCESS(f"test account ready: phone={phone}, openid={openid}"))
