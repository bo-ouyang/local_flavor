from django.conf import settings

from community.models import CommunityAuditStatus, CommunityComment, CommunityPost
from config.celery import app
from messaging.services import send_system_notice


def _audit_text(content: str) -> tuple[str, str]:
    banned_words = getattr(settings, "COMMUNITY_AUDIT_BANNED_WORDS", [])
    normalized = (content or "").strip().lower()
    for word in banned_words:
        check = word.strip().lower()
        if check and check in normalized:
            return CommunityAuditStatus.REJECTED, f"Contains banned word: {word}"
    return CommunityAuditStatus.APPROVED, ""


def notify_comment_approved(comment: CommunityComment) -> None:
    item_title = getattr(comment.post.item, "title", "相关特产")
    commenter_name = comment.user.nickname or f"用户{comment.user_id}"
    if comment.post.user_id != comment.user_id:
        send_system_notice(
            comment.post.user_id,
            f"{commenter_name} 评论了你关于「{item_title}」的社区动态。",
            comment.post.item_id,
        )
    parent = comment.parent
    if parent and parent.user_id not in (comment.user_id, comment.post.user_id):
        send_system_notice(
            parent.user_id,
            f"{commenter_name} 回复了你在「{item_title}」下的评论。",
            comment.post.item_id,
        )


def notify_post_liked(post: CommunityPost, liker_name: str) -> None:
    if post.user_id <= 0:
        return
    item_title = getattr(post.item, "title", "相关特产")
    send_system_notice(
        post.user_id,
        f"{liker_name} 点赞了你关于「{item_title}」的社区动态。",
        post.item_id,
    )


def notify_post_audit_result(post: CommunityPost) -> None:
    item_title = getattr(post.item, "title", "相关特产")
    if post.audit_status == CommunityAuditStatus.APPROVED:
        send_system_notice(
            post.user_id,
            f"你关于「{item_title}」的社区动态已审核通过，其他用户现在可以看到这条内容了。",
            post.item_id,
        )
        return
    if post.audit_status == CommunityAuditStatus.REJECTED:
        reason = (post.audit_reason or "").strip()
        suffix = f"。原因：{reason}" if reason else "。"
        send_system_notice(
            post.user_id,
            f"你关于「{item_title}」的社区动态未通过审核{suffix}",
            post.item_id,
        )


@app.task
def audit_community_post(post_id: int):
    post = CommunityPost.objects.select_related("item").filter(id=post_id).first()
    if not post:
        return {"status": "missing"}

    previous_status = post.audit_status
    status, reason = _audit_text(post.content)
    post.audit_status = status
    post.audit_reason = reason
    post.save(update_fields=["audit_status", "audit_reason", "updated_at"])
    if status != previous_status and status in (
        CommunityAuditStatus.APPROVED,
        CommunityAuditStatus.REJECTED,
    ):
        notify_post_audit_result(post)
    return {"status": status, "reason": reason}


@app.task
def audit_community_comment(comment_id: int):
    comment = (
        CommunityComment.objects.select_related("post", "post__item", "user", "parent", "parent__user")
        .filter(id=comment_id)
        .first()
    )
    if not comment:
        return {"status": "missing"}

    previous_status = comment.audit_status
    status, reason = _audit_text(comment.content)
    comment.audit_status = status
    comment.audit_reason = reason
    comment.save(update_fields=["audit_status", "audit_reason"])

    if status == CommunityAuditStatus.APPROVED and previous_status != CommunityAuditStatus.APPROVED:
        notify_comment_approved(comment)
    return {"status": status, "reason": reason}
