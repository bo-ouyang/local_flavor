from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


def _perm_codename(action: str, model_name: str) -> str:
    return f"{action}_{model_name}"


def _collect_model_permissions(app_label: str, model_name: str, actions: list[str]):
    codenames = [_perm_codename(action, model_name) for action in actions]
    return Permission.objects.filter(content_type__app_label=app_label, codename__in=codenames)


class Command(BaseCommand):
    help = "Initialize RBAC roles for Django admin"

    ROLE_MATRIX = {
        "super_admin": {
            "all_permissions": True,
        },
        "ops_admin": {
            "models": [
                ("users", "localuser", ["view", "change"]),
                ("users", "region", ["view", "add", "change"]),
                ("items", "item", ["view", "change"]),
                ("interactions", "comment", ["view", "change", "delete"]),
                ("messaging", "message", ["view", "change", "delete"]),
                ("exchange", "exchangerequest", ["view", "change"]),
                ("system_config", "systemoption", ["view", "add", "change"]),
            ]
        },
        "content_admin": {
            "models": [
                ("items", "item", ["view", "add", "change", "delete"]),
                ("interactions", "comment", ["view", "add", "change", "delete"]),
                ("interactions", "flavortag", ["view", "add", "change", "delete"]),
                ("interactions", "flavorvote", ["view", "delete"]),
                ("system_config", "systemoption", ["view", "change"]),
            ]
        },
        "support_admin": {
            "models": [
                ("users", "localuser", ["view"]),
                ("items", "item", ["view"]),
                ("exchange", "exchangerequest", ["view", "change"]),
                ("messaging", "message", ["view"]),
                ("interactions", "comment", ["view"]),
            ]
        },
        "auditor": {
            "models": [
                ("users", "localuser", ["view"]),
                ("users", "region", ["view"]),
                ("items", "item", ["view"]),
                ("interactions", "comment", ["view"]),
                ("interactions", "flavortag", ["view"]),
                ("messaging", "message", ["view"]),
                ("exchange", "exchangerequest", ["view"]),
                ("system_config", "systemoption", ["view"]),
            ]
        },
    }

    def handle(self, *args, **options):
        all_permissions = Permission.objects.all()

        for role_name, role_config in self.ROLE_MATRIX.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            group.permissions.clear()

            if role_config.get("all_permissions"):
                group.permissions.add(*all_permissions)
                self.stdout.write(self.style.SUCCESS(f"[RBAC] {role_name}: all permissions"))
                continue

            role_permissions = Permission.objects.none()
            for app_label, model_name, actions in role_config.get("models", []):
                role_permissions |= _collect_model_permissions(app_label, model_name, actions)

            group.permissions.add(*role_permissions)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[RBAC] {role_name}: {role_permissions.count()} permissions assigned"
                )
            )

        self.stdout.write(self.style.SUCCESS("RBAC roles initialized."))
