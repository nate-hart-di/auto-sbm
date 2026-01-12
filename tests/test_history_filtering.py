import pytest
from datetime import datetime, timezone
from sbm.utils.tracker import filter_runs


class TestHistoryFiltering:
    def test_filter_limit(self):
        runs = [{"id": i} for i in range(10)]
        result = filter_runs(runs, limit=5)
        assert len(result) == 5
        # Assuming limit returns most recent (first N after sorting)
        # Verify order/selection if implementation sorts

    def test_filter_since_until(self):
        runs = [
            {"timestamp": "2024-01-01T10:00:00Z"},
            {"timestamp": "2024-01-02T10:00:00Z"},
            {"timestamp": "2024-01-03T10:00:00Z"},
        ]

        # Test Since
        result_since = filter_runs(runs, since="2024-01-02")
        assert len(result_since) == 2

        # Test Until
        result_until = filter_runs(runs, until="2024-01-02")
        assert len(result_until) == 2

        # Test Range
        result_range = filter_runs(runs, since="2024-01-02", until="2024-01-02")
        assert len(result_range) == 1

    def test_filter_user(self):
        runs = [
            {"_user": "user1", "id": 1},
            {"user_id": "user2", "id": 2},
            {"_user": "user1", "id": 3},
        ]

        result = filter_runs(runs, user="user1")
        assert len(result) == 2
        assert all(r.get("_user") == "user1" for r in result)

    def test_filter_invalid_dates(self):
        runs = [{"timestamp": "2024-01-01T10:00:00Z"}]
        # Should gracefully handle invalid dates (log warning, ignore filter)
        result = filter_runs(runs, since="invalid-date")
        assert len(result) == 1
