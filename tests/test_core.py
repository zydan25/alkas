from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.auth.routes import _safe_next
from app.accounting.models import JournalLine
from app.reports.services import date_bounds
from app.policies.services import cancellation_refund_percent
from app.pricing.services import _time_matches


def test_safe_next_rejects_external_urls():
    assert _safe_next("/customer") == "/customer"
    assert _safe_next("https://example.com") is None
    assert _safe_next("//example.com") is None


def test_journal_line_is_one_sided():
    assert JournalLine.amount_is_valid(Decimal("10"), Decimal("0"))
    assert JournalLine.amount_is_valid(Decimal("0"), Decimal("10"))
    assert not JournalLine.amount_is_valid(Decimal("0"), Decimal("0"))
    assert not JournalLine.amount_is_valid(Decimal("10"), Decimal("5"))


def test_date_bounds_is_full_day_window():
    start, end = date_bounds(date(2026, 9, 22), date(2026, 9, 22))
    assert start == datetime(2026, 9, 22, tzinfo=timezone.utc)
    assert end == datetime(2026, 9, 23, tzinfo=timezone.utc)


def test_time_match_supports_overnight_window():
    from datetime import time
    assert _time_matches(time(23, 0), time(20, 0), time(2, 0))
    assert _time_matches(time(1, 0), time(20, 0), time(2, 0))
    assert not _time_matches(time(12, 0), time(20, 0), time(2, 0))


def test_refund_policy_cutoff():
    class Policy:
        cancellation_deadline_minutes = 360
        refund_percent_before_deadline = 100
        refund_percent_after_deadline = 0

    now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
    start = now + timedelta(minutes=360)
    assert cancellation_refund_percent(Policy(), start, now) == Decimal("100")

    after = now + timedelta(minutes=359)
    assert cancellation_refund_percent(Policy(), after, now) == Decimal("0")


def test_root_account_is_never_postable():
    from app.accounting.models import Account
    root = Account(code="1000", name_ar="الأصول", account_type="asset", is_active=True, is_control=False)
    assert root.is_postable is False


def test_account_with_child_is_not_postable():
    from app.accounting.models import Account
    parent = Account(code="1100", name_ar="الصندوق", account_type="asset", parent_id=1, is_active=True, is_control=False)
    child = Account(code="110001", name_ar="صندوق الاستقبال", account_type="asset", parent_id=2, is_active=True, is_control=False)
    parent.children.append(child)
    assert parent.is_postable is False
    assert child.is_postable is True
