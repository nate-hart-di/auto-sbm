try:
    # Need to simulate MigrationResult interface if MigrationReportData expects it?
    # Actually generate_migration_report takes MigrationReportData or MigrationResult?
    # The signature in report_generator.py line 72: def generate_migration_report(result: "MigrationResult")
    # But MigrationReportData is a dataclass wrapper?
    # Wait, looking at my edit in Step 510:
    # I imported MigrationReportData, created an instance `report_data`, and passed it to `generate_migration_report`.
    # Let me check report_generator.py again.
    # Line 26: class MigrationReportData
    # Line 72: def generate_migration_report(result: "MigrationResult")
    # AND inside `_build_report_content`: `result.lines_migrated`, etc.
    # Does `MigrationReportData` mimic `MigrationResult`?
    # Line 30: "Extends MigrationResult with additional..."
    # If I pass MigrationReportData to a function expecting MigrationResult (duck typing), it should work if attributes match.
    # The attributes used in `_build_report_content` are `slug`, `status`, `elapsed_time`, `lines_migrated`, `pr_url`, `branch_name`, `salesforce_message`.
    # MigrationReportData HAS these fields.
    from sbm.utils.report_generator import MigrationReportData, generate_migration_report
except ImportError:
    import sys

    sys.path.append("/Users/nathanhart/auto-sbm")
    from sbm.utils.report_generator import MigrationReportData, generate_migration_report

import os
from pathlib import Path


def test_report_generation():
    print("Testing Report Generation...")

    # Dummy data using the Dataclass
    data = MigrationReportData(
        slug="test-slug-123",
        status="success",
        elapsed_time=120.5,
        lines_migrated=1000,
        files_created=[{"path": "sb-home.scss", "lines": 200, "size_bytes": 1024}],
        pr_url="https://github.com/example/repo/pull/1",
        salesforce_message="- Component A: mapped\n- Component B: skipped",
    )
    # Manually populate fields if __post_init__/init doesn't cover mismatch
    data.files_created_count = 4

    # Generate
    path_str = generate_migration_report(data)

    if path_str and Path(path_str).exists():
        print(f"✅ Report generated successfully at: {path_str}")
        print("Content preview:")
        print(Path(path_str).read_text()[:300])

        # Cleanup
        os.remove(path_str)
        print("Report cleaned up.")
    else:
        print("❌ Report generation failed.")


if __name__ == "__main__":
    test_report_generation()
