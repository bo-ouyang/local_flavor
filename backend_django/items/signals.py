from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache_utils import bump_namespace_version
from interactions.models import FlavorTag
from items.models import Item


@receiver(post_save, sender=Item)
@receiver(post_delete, sender=Item)
def _on_item_changed(**_kwargs):
    bump_namespace_version("items")
    bump_namespace_version("item_detail")


@receiver(post_save, sender=FlavorTag)
@receiver(post_delete, sender=FlavorTag)
def _on_flavor_tag_changed(**_kwargs):
    bump_namespace_version("items")
    bump_namespace_version("item_detail")
