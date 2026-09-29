"""settings.py: .env parsing and the Pacific quota day (resets 12:30 PM IST in PDT, 1:30 PM IST in PST)."""

from datetime import UTC, datetime, timedelta, timezone

from api.settings import _parse_env_value, next_quota_reset, pacific_date

IST = timezone(timedelta(hours=5, minutes=30))


def test_env_value_parsing():
    assert _parse_env_value(' "abc" ') == "abc"
    assert _parse_env_value('"abc"TRAILING="x"') == "abc"
    assert _parse_env_value("abc # comment") == "abc"


def test_quota_day_rolls_at_1230_ist_during_pdt():
    assert pacific_date(datetime(2026, 9, 28, 12, 29, tzinfo=IST)) == "2026-09-27"
    assert pacific_date(datetime(2026, 9, 28, 12, 30, tzinfo=IST)) == "2026-09-28"


def test_quota_day_rolls_at_1330_ist_during_pst():
    # DST ends 1 Nov 2026; from then the reset is 1:30 PM IST.
    assert pacific_date(datetime(2026, 11, 10, 13, 29, tzinfo=IST)) == "2026-11-09"
    assert pacific_date(datetime(2026, 11, 10, 13, 30, tzinfo=IST)) == "2026-11-10"


def test_dst_boundaries_2026():
    # 8 Mar 2026 02:00 PST = 10:00 UTC; 1 Nov 2026 02:00 PDT = 09:00 UTC
    assert pacific_date(datetime(2026, 3, 8, 7, 59, tzinfo=UTC)) == "2026-03-07"
    assert pacific_date(datetime(2026, 3, 8, 8, 0, tzinfo=UTC)) == "2026-03-08"


def test_next_reset_is_midnight_pacific():
    now = datetime(2026, 9, 28, 10, 0, tzinfo=IST)
    assert next_quota_reset(now).astimezone(IST) == datetime(2026, 9, 28, 12, 30, tzinfo=IST)
    later = datetime(2026, 11, 20, 14, 0, tzinfo=IST)
    assert next_quota_reset(later).astimezone(IST) == datetime(2026, 11, 21, 13, 30, tzinfo=IST)
