from datetime import datetime, timedelta, timezone

from sbm.utils.tracker import _parse_date_input


def test_parse_specific_day():
    # MM/DD/YY
    res = _parse_date_input("01/25/25")
    assert res is not None
    start, end = res
    assert start == datetime(2025, 1, 25, tzinfo=timezone.utc)
    assert end == start + timedelta(days=1)

    # M/D/YY
    res = _parse_date_input("1/2/26")
    assert res is not None
    start, end = res
    assert start == datetime(2026, 1, 2, tzinfo=timezone.utc)


def test_parse_specific_month():
    # MM/YY
    res = _parse_date_input("01/25")
    assert res is not None
    start, end = res
    assert start == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert end == datetime(2025, 2, 1, tzinfo=timezone.utc)

    # Dec month rollover
    res = _parse_date_input("12/24")
    assert res is not None
    start, end = res
    assert start == datetime(2024, 12, 1, tzinfo=timezone.utc)
    assert end == datetime(2025, 1, 1, tzinfo=timezone.utc)


def test_parse_date_to_date_range():
    res = _parse_date_input("1/1/25 to 2/28/25")
    assert res is not None
    start, end = res
    assert start == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert end == datetime(2025, 3, 1, tzinfo=timezone.utc)  # end_dt is 1 day after end of Feb 28


def test_parse_duration_range():
    # 14 1/1/26
    res = _parse_date_input("14 1/1/26")
    assert res is not None
    start, end = res
    assert start == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert end == start + timedelta(days=14)


def test_parse_invalid():
    assert _parse_date_input("not a date") is None
    assert _parse_date_input("13/45/25") is None  # Invalid month/day
