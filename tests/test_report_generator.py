from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbm.utils.report_generator import generate_migration_report


class TestReportGenerator:
    @pytest.fixture
    def mock_reports_dir(self, tmp_path):
        reports_dir = tmp_path / ".sbm-reports"
        with patch("sbm.utils.report_generator.REPORTS_DIR", reports_dir):
            yield reports_dir

    def test_generate_report_success(self, mock_reports_dir):
        # Setup
        result = MagicMock()
        result.slug = "test-theme"
        result.status = "success"
        result.elapsed_time = 60.0
        result.lines_migrated = 800
        result.pr_url = "http://github.com/pr/1"
        result.branch_name = "feat/migration"
        result.salesforce_message = "- component 1\n- component 2"

        # Execute
        report_path = generate_migration_report(result)

        # Verify
        assert report_path is not None
        path = Path(report_path)
        assert path.exists()
        assert path.parent == mock_reports_dir

        content = path.read_text()
        assert "# Migration Report: test-theme" in content
        assert "✅ SUCCESS" in content
        assert "1m 0s" in content
        assert "1.0 hours" in content
        assert "http://github.com/pr/1" in content

    def test_generate_report_failed(self, mock_reports_dir):
        # Setup
        result = MagicMock()
        result.slug = "failed-theme"
        result.status = "failed"
        result.error_message = "Something went wrong"
        # Mock step_failed to behave like an Enum or just a string that the code handles
        mock_step = MagicMock()
        mock_step.value = "SCSS_MIGRATION"
        result.step_failed = mock_step

        # Execute
        report_path = generate_migration_report(result)

        # Verify
        content = Path(report_path).read_text(encoding="utf-8")
        assert "❌ **Status:** FAILED" in content
        assert "Something went wrong" in content
        assert "SCSS_MIGRATION" in content

    def test_update_index(self, mock_reports_dir):
        # Setup
        mock_reports_dir.mkdir(parents=True, exist_ok=True)
        result = MagicMock()
        result.slug = "index-test"
        result.status = "success"
        result.elapsed_time = 10.0
        result.lines_migrated = 100

        # Execute
        generate_migration_report(result)

        # Verify Index
        index_path = mock_reports_dir / "index.md"
        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")
        # Check for presence of key elements rather than exact spacing to be robust
        assert "index-test" in content
        assert "✅" in content
