from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache_utils import bump_namespace_version
from system_config.models import SystemOption


@receiver(post_save, sender=SystemOption)
def _on_option_saved(**_kwargs):
    bump_namespace_version("options")


@receiver(post_delete, sender=SystemOption)
def _on_option_deleted(**_kwargs):
    bump_namespace_version("options")
