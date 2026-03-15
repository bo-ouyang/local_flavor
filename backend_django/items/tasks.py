from django.conf import settings

from config.celery import app
from items.models import Item, ItemAuditStatus


def _audit_item_text(*parts: str) -> tuple[str, str]:
    normalized = " ".join((part or "").strip().lower() for part in parts)
    for word in getattr(settings, "ITEM_AUDIT_BANNED_WORDS", []):
        check = word.strip().lower()
        if check and check in normalized:
            return ItemAuditStatus.REJECTED, f"Contains banned word: {word}"
    return ItemAuditStatus.APPROVED, ""


@app.task
def audit_item(item_id: int):
    item = Item.objects.filter(id=item_id).first()
    if not item:
        return {"status": "missing"}

    status, reason = _audit_item_text(item.title, item.description, item.eat_method)
    item.audit_status = status
    item.audit_reason = reason
    item.save(update_fields=["audit_status", "audit_reason", "updated_at"])
    return {"status": status, "reason": reason}

@app.task
def sync_user_preference_task(user_id: int):
    from items.recommendation import sync_user_preference
    sync_user_preference(user_id)
