from typing import Dict, Iterable, List, Optional, Tuple

from django.db.models import Count, F
from django.db.models import Q
from django.utils import timezone

from core.time_utils import get_current_season
from exchange.models import ExchangeRequest, ExchangeStatus
from interactions.models import FlavorVote
from items.models import Item
from users.models import LocalUser, UserPreferenceSnapshot


def sync_user_preference(user_id: int):
    """
    Recalculate and update the UserPreferenceSnapshot for the given user.
    """
    try:
        user = LocalUser.objects.get(id=user_id)
    except LocalUser.DoesNotExist:
        return

    # 1. Collect Flavor Preferences
    # Recent votes
    flavor_votes = FlavorVote.objects.filter(user_id=user_id).select_related("flavor_tag")
    flavor_counts = {}
    for vote in flavor_votes:
        tag_name = vote.flavor_tag.tag_name
        flavor_counts[tag_name] = flavor_counts.get(tag_name, 0) + 1

    # 2. Collect Category Preferences from posted items
    posted_items = Item.objects.filter(user_id=user_id).values("category").annotate(count=Count('id'))
    category_weights = {}
    for row in posted_items:
        category_weights[row['category']] = row['count']

    # 3. Collect Region Preferences & Completed Exchanges
    completed_exchanges = ExchangeRequest.objects.filter(
        status=ExchangeStatus.COMPLETED
    ).filter(
        Q(requester_id=user_id) | Q(owner_id=user_id)
    ).select_related("requested_item", "offered_item")

    exchange_completed_count = completed_exchanges.count()
    region_weights = {}
    
    for ex in completed_exchanges:
        # Check items involved
        items_involved = []
        if ex.requested_item:
            items_involved.append(ex.requested_item)
        if ex.offered_item:
            items_involved.append(ex.offered_item)
            
        for item in items_involved:
            # Weigh categories involved in successful exchanges more heavily
            category_weights[item.category] = category_weights.get(item.category, 0) + 2
            
            # Weigh flavors involved
            for tag in item.flavor_tags.all():
                flavor_counts[tag.tag_name] = flavor_counts.get(tag.tag_name, 0) + 2
                
            # Region weights
            if item.region_code:
                region_weights[item.region_code] = region_weights.get(item.region_code, 0) + 1

    # Sort flavors to create a vector (top 10)
    sorted_flavors = sorted(flavor_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    flavor_vector = [f[0] for f in sorted_flavors]

    snapshot, _ = UserPreferenceSnapshot.objects.get_or_create(user_id=user_id)
    snapshot.flavor_vector = flavor_vector
    snapshot.category_weights = category_weights
    snapshot.region_weights = region_weights
    snapshot.exchange_completed_count = exchange_completed_count
    snapshot.save()


def get_publisher_completed_counts(user_ids: Iterable[int]) -> Dict[int, int]:
    normalized_ids = {int(user_id) for user_id in user_ids if user_id}
    if not normalized_ids:
        return {}

    counts = {user_id: 0 for user_id in normalized_ids}
    requester_rows = (
        ExchangeRequest.objects.filter(
            status=ExchangeStatus.COMPLETED,
            requester_id__in=normalized_ids,
        )
        .values("requester_id")
        .annotate(total=Count("id"))
    )
    owner_rows = (
        ExchangeRequest.objects.filter(
            status=ExchangeStatus.COMPLETED,
            owner_id__in=normalized_ids,
        )
        .exclude(owner_id=F("requester_id"))
        .values("owner_id")
        .annotate(total=Count("id"))
    )
    for row in requester_rows:
        counts[row["requester_id"]] += row["total"]
    for row in owner_rows:
        counts[row["owner_id"]] += row["total"]
    return counts


def score_item_for_user(
    item: Item,
    user: LocalUser,
    snapshot: UserPreferenceSnapshot,
    publisher_completed_count: Optional[int] = None,
) -> Tuple[float, List[str]]:
    """
    Score an item based on the user's preference snapshot.
    Returns (score, reason_tags)
    Total Score = Flavor(35%) + Category(20%) + Season(15%) + Region(10%) + ExchangeExperience(10%) + Freshness(10%)
    """
    score = 0.0
    reason_tags = []

    # 1. Flavor Preference (35%)
    flavor_score = 0.0
    item_tags = [t.tag_name for t in item.flavor_tags.all()]
    matched_flavors = set(item_tags).intersection(set(snapshot.flavor_vector))
    if matched_flavors:
        flavor_score = 0.35 * (len(matched_flavors) / max(1, len(snapshot.flavor_vector)))
        score += flavor_score
        reason_tags.append(f"偏好{list(matched_flavors)[0]}")

    # 2. Category Preference (20%)
    cat_weight = snapshot.category_weights.get(item.category, 0)
    if cat_weight > 0:
        score += 0.20
        # Don't add a reason tag for just category to avoid clutter, unless it's very high
    
    # 3. Season Match (15%)
    current_season = get_current_season()
    if item.season == current_season:
        score += 0.15
        reason_tags.append("当季推荐")

    # 4. Region Relevance (10%)
    if item.region_code == user.region_code:
        score += 0.10
        reason_tags.append("同城优先")
    elif item.region_code in snapshot.region_weights:
        # Match based on history of exchanges
        score += 0.05
        reason_tags.append("常换地区")

    # 5. Exchange Experience (10%)
    # Use the number of completed exchanges involving the publisher.
    publisher_completed = publisher_completed_count
    if publisher_completed is None:
        publisher_completed = (
            ExchangeRequest.objects.filter(status=ExchangeStatus.COMPLETED)
            .filter(Q(requester_id=item.user_id) | Q(owner_id=item.user_id))
            .count()
        )
    if publisher_completed > 0:
        score += min(0.10, publisher_completed * 0.02)
        if publisher_completed > 5:
            reason_tags.append("交换经验丰富")

    # 6. Freshness (10%)
    days_old = (timezone.now() - item.created_at).days
    if days_old <= 7:
        score += 0.10
        reason_tags.append("新鲜发布")
    elif days_old <= 30:
        score += 0.05

    # Deduplicate and limit reason tags
    unique_tags = []
    for t in reason_tags:
        if t not in unique_tags:
            unique_tags.append(t)
            
    return round(score, 3), unique_tags[:3]
