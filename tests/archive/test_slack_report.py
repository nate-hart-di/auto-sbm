import unittest
import json
from datetime import datetime, timedelta, timezone
from scripts.stats.report_slack import (
    AUTO_SBM_OPEN_PRS_URL,
    calculate_metrics,
    filter_runs_by_date,
    format_slack_payload,
)


class TestSlackReport(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.runs = [
            {
                "timestamp": self.now.isoformat(),
                "merged_at": self.now.isoformat(),
                "status": "success",
                "lines_migrated": 800,
                "automation_seconds": 3600,
                "_user": "user1",
                "slug": "dealer-one",
            },
            {
                "timestamp": (self.now - timedelta(hours=12)).isoformat(),
                "status": "failed",
                "lines_migrated": 0,
                "automation_seconds": 100,
                "_user": "user2",
                "slug": "dealer-two",
            },
            {
                "timestamp": (self.now - timedelta(days=2)).isoformat(),
                "merged_at": (self.now - timedelta(days=2)).isoformat(),
                "status": "success",
                "lines_migrated": 1600,
                "automation_seconds": 7200,
                "_user": "user1",
                "slug": "dealer-one",
            },
        ]

    def test_filter_runs_by_date(self):
        # Should only get the 2 runs from today (0 and 1)
        filtered = filter_runs_by_date(self.runs, "1")
        self.assertEqual(len(filtered), 2)

        # Should get all 3 runs
        filtered_3days = filter_runs_by_date(self.runs, "3")
        self.assertEqual(len(filtered_3days), 3)

    def test_calculate_metrics(self):
        # Test on the filtered set (today only)
        filtered = filter_runs_by_date(self.runs, "1")
        metrics = calculate_metrics(filtered, user_migrations={})

        self.assertEqual(metrics["total_runs"], 2)
        self.assertEqual(metrics["success_count"], 1)
        self.assertEqual(metrics["success_rate"], 50.0)
        self.assertEqual(metrics["lines_migrated"], 800)
        self.assertEqual(metrics["time_saved_hours"], 1.0)  # 800 lines / 800
        self.assertEqual(metrics["top_contributors"][0][0], "user1")

    def test_format_payload(self):
        filtered = filter_runs_by_date(self.runs, "1")
        metrics = calculate_metrics(filtered, user_migrations={})
        payload = format_slack_payload(metrics, "1", current_in_review_count=0)

        self.assertIn("SBM Stats:", payload["text"])
        # Check blocks
        self.assertEqual(payload["blocks"][0]["type"], "header")
        self.assertNotIn("Success Rate", json.dumps(payload))
        self.assertIn(AUTO_SBM_OPEN_PRS_URL, json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
