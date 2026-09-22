from decimal import Decimal
from ..models import Resource
from .models import PriceOverride, PriceRule

def _time_matches(value, start, end):
    if start is None or end is None:
        return True
    if start <= end:
        return start <= value < end
    return value >= start or value < end

def calculate_price(resource, start_at, end_at):
    minutes = max(1, int((end_at - start_at).total_seconds() / 60))
    override = PriceOverride.query.filter(
        PriceOverride.resource_id == resource.id,
        PriceOverride.is_active.is_(True),
        PriceOverride.starts_at < end_at,
        PriceOverride.ends_at > start_at,
    ).order_by(PriceOverride.id.desc()).first()
    if override:
        return (Decimal(override.price_per_hour) * Decimal(minutes) / Decimal(60)).quantize(Decimal("0.01"))

    candidates = []
    for rule in PriceRule.query.filter_by(is_active=True).order_by(PriceRule.priority.desc(), PriceRule.id.desc()).all():
        if rule.resource_id and rule.resource_id != resource.id:
            continue
        if rule.sport_id and rule.sport_id != resource.sport_id:
            continue
        if rule.weekday is not None and rule.weekday != start_at.weekday():
            continue
        if rule.valid_from and start_at.date() < rule.valid_from:
            continue
        if rule.valid_to and start_at.date() > rule.valid_to:
            continue
        if rule.min_minutes and minutes < rule.min_minutes:
            continue
        if rule.max_minutes and minutes > rule.max_minutes:
            continue
        if not _time_matches(start_at.timetz().replace(tzinfo=None), rule.start_time, rule.end_time):
            continue
        candidates.append(rule)

    rate = Decimal(candidates[0].price_per_hour) if candidates else Decimal(resource.base_price or 0)
    return (rate * Decimal(minutes) / Decimal(60)).quantize(Decimal("0.01"))
