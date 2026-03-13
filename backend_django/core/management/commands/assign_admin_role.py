from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Assign one RBAC role(group) to a Django admin user"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Django auth username")
        parser.add_argument("--role", required=True, help="RBAC role name, e.g. ops_admin")

    def handle(self, *args, **options):
        username = options["username"]
        role = options["role"]

        user = User.objects.filter(username=username).first()
        if not user:
            raise CommandError(f"user not found: {username}")

        group = Group.objects.filter(name=role).first()
        if not group:
            raise CommandError(f"role(group) not found: {role}. Run `python manage.py init_rbac` first.")

        user.is_staff = True
        user.groups.add(group)
        user.save(update_fields=["is_staff"])
        self.stdout.write(self.style.SUCCESS(f"[RBAC] assigned role `{role}` to `{username}`"))
