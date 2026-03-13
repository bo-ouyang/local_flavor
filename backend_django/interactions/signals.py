from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache_utils import bump_namespace_version
from interactions.models import Comment


@receiver(post_save, sender=Comment)
@receiver(post_delete, sender=Comment)
def _on_comment_changed(**_kwargs):
    bump_namespace_version("comments")
