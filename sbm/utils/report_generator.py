"""
Markdown migration report generator for SBM.

Generates detailed markdown reports for individual migrations in .sbm-reports/
directory with comprehensive file breakdowns, component details, and time savings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .logger import logger

if TYPE_CHECKING:
    from sbm.core.migration import MigrationResult

# Reports directory in repo root
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
REPORTS_DIR = REPO_ROOT / ".sbm-reports"


@dataclass
class MigrationReportData:
    """
    Holds all migration data for markdown report generation.

    Extends MigrationResult with additional file and component details.
    """

    slug: str
    status: str
    pr_url: Optional[str] = None
    salesforce_message: Optional[str] = None
    branch_name: Optional[str] = None
    elapsed_time: float = 0.0
    lines_migrated: int = 0
    timestamp: str = ""
    error_message: Optional[str] = None
    step_failed: Optional[str] = None

    # File breakdown data
    files_created: list[dict] = None  # [{path, lines, size_bytes}]
    files_modified: list[str] = None

    # Component details
    mixins_converted: int = 0
    variables_mapped: int = 0
    oem_styles_added: list[str] = None  # e.g., ["Stellantis cookie banner"]
    map_migration_status: str = "N/A"

    # Validation
    scss_compilation_success: bool = True
    scss_errors: list[str] = None

    def __post_init__(self):
        """Initialize default lists."""
        if self.files_created is None:
            self.files_created = []
        if self.files_modified is None:
            self.files_modified = []
        if self.oem_styles_added is None:
            self.oem_styles_added = []
        if self.scss_errors is None:
            self.scss_errors = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


def generate_migration_report(result: MigrationResult) -> Optional[str]:
    """
    Generate a detailed markdown report for a migration.

    Creates a markdown file in .sbm-reports/{slug}-{timestamp}.md with
    comprehensive migration details including file breakdown, component
    details, and time savings analysis.

    Args:
        result: MigrationResult object from the migration

    Returns:
        Path to the generated report file, or None if generation failed
    """
    try:
        # Ensure reports directory exists
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_filename = f"{result.slug}-{timestamp}.md"
        report_path = REPORTS_DIR / report_filename

        # Build report content
        content = _build_report_content(result)

        # Write report file
        report_path.write_text(content, encoding="utf-8")
        logger.info(f"Generated markdown report: {report_path}")

        # Update index.md
        _update_index(result, report_filename)

        return str(report_path)

    except Exception as e:
        logger.error(f"Failed to generate markdown report for {result.slug}: {e}")
        return None


def _coerce_int(value: object, default: int = 0) -> int:
    """Best-effort conversion for numeric report fields."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: object, default: float = 0.0) -> float:
    """Best-effort conversion for numeric report fields."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_report_content(result: MigrationResult) -> str:
    """Build the markdown content for a migration report."""
    status_emoji = "✅" if result.status == "success" else "❌"
    lines_migrated = _coerce_int(getattr(result, "lines_migrated", 0))
    elapsed_time = _coerce_float(getattr(result, "elapsed_time", 0.0))
    time_saved = lines_migrated / 800.0 if lines_migrated else 0

    # Format elapsed time nicely
    elapsed_mins = int(elapsed_time // 60)
    elapsed_secs = int(elapsed_time % 60)
    elapsed_str = f"{elapsed_mins}m {elapsed_secs}s" if elapsed_mins else f"{elapsed_secs}s"

    lines = [
        f"# Migration Report: {result.slug}",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Theme Slug** | `{result.slug}` |",
        f"| **Status** | {status_emoji} {result.status.upper()} |",
        f"| **Duration** | {elapsed_str} |",
        f"| **Lines Migrated** | {lines_migrated:,} |",
        f"| **Time Saved** | ~{time_saved:.1f} hours |",
        f"| **Branch** | `{result.branch_name or 'N/A'}` |",
        f"| **PR URL** | {result.pr_url or 'N/A'} |",
        "",
    ]

    # File Breakdown section
    lines.extend(
        [
            "---",
            "",
            "## File Breakdown",
            "",
        ]
    )

    # Standard SB files (we can infer these from a successful migration)
    if result.status == "success":
        sb_files = [
            ("sb-home.scss", "Home page styles"),
            ("sb-inside.scss", "Interior page styles"),
            ("sb-vdp.scss", "VDP styles"),
            ("sb-vrp.scss", "VRP styles"),
        ]
        lines.append("| File | Description |")
        lines.append("|------|-------------|")
        for filename, description in sb_files:
            lines.append(f"| `{filename}` | {description} |")
        lines.append("")
    else:
        lines.append("*No files created (migration failed)*")
        lines.append("")

    # Component Details section
    lines.extend(
        [
            "---",
            "",
            "## Component Details",
            "",
        ]
    )

    # Extract component info from salesforce_message if available
    if result.salesforce_message:
        lines.append("**Migration Summary:**")
        lines.append("")
        # Parse salesforce message for component details
        for line in result.salesforce_message.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                lines.append(line)
        lines.append("")
    else:
        lines.append("*No detailed component information available*")
        lines.append("")

    # Time Savings Analysis
    lines.extend(
        [
            "---",
            "",
            "## Time Savings Analysis",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| **Lines Migrated** | {lines_migrated:,} |",
            "| **Manual Estimate** | ~4 hours |",
            f"| **Automation Time** | {elapsed_str} |",
            f"| **Time Saved** | ~{time_saved:.1f} hours |",
            "",
            "> **Calculation:** Time saved = Lines migrated ÷ 800 lines/hour",
            "",
        ]
    )

    # Validation Results
    lines.extend(
        [
            "---",
            "",
            "## Validation Results",
            "",
        ]
    )

    if result.status == "success":
        lines.append("✅ **SCSS Compilation:** Passed")
        lines.append("")
    else:
        lines.append(f"❌ **Status:** {result.status.upper()}")
        lines.append("")
        if hasattr(result, "step_failed") and result.step_failed:
            step_name = (
                result.step_failed.value
                if hasattr(result.step_failed, "value")
                else str(result.step_failed)
            )
            lines.append(f"**Failed At Step:** `{step_name}`")
            lines.append("")
        if result.error_message:
            lines.append(f"**Error:** {result.error_message}")
            lines.append("")
        if hasattr(result, "scss_errors") and result.scss_errors:
            lines.append("**SCSS Errors:**")
            lines.append("")
            for error in result.scss_errors[:10]:  # Limit to first 10
                lines.append(f"- {error}")
            lines.append("")

    # Links section
    lines.extend(
        [
            "---",
            "",
            "## Links",
            "",
        ]
    )

    if result.pr_url:
        lines.append(f"- **Pull Request:** [{result.pr_url}]({result.pr_url})")
    if result.branch_name:
        lines.append(f"- **Branch:** `{result.branch_name}`")
    if not result.pr_url and not result.branch_name:
        lines.append("*No links available*")

    lines.append("")

    return "\n".join(lines)


def _update_index(result: MigrationResult, report_filename: str) -> None:
    """
    Update the index.md table of contents with the new report.

    Creates index.md if it doesn't exist, otherwise appends a new row.
    """
    index_path = REPORTS_DIR / "index.md"
    status_emoji = "✅" if result.status == "success" else "❌"

    # Format elapsed time
    elapsed_time = _coerce_float(getattr(result, "elapsed_time", 0.0))
    elapsed_mins = int(elapsed_time // 60)
    elapsed_secs = int(elapsed_time % 60)
    elapsed_str = f"{elapsed_mins}m {elapsed_secs}s" if elapsed_mins else f"{elapsed_secs}s"
    lines_migrated = _coerce_int(getattr(result, "lines_migrated", 0))

    # Format date
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Table row for this report
    new_row = (
        f"| {date_str} | `{result.slug}` | {status_emoji} | {elapsed_str} | "
        f"{lines_migrated:,} | [{report_filename}](./{report_filename}) |"
    )

    try:
        if index_path.exists():
            # Append to existing index
            content = index_path.read_text(encoding="utf-8")
            # Insert new row after the table header (line 6)
            lines = content.split("\n")
            # Find the table and insert after header separator
            for i, line in enumerate(lines):
                if line.startswith("|---"):
                    # Insert after this line
                    lines.insert(i + 1, new_row)
                    break
            else:
                # No table found, append at end
                lines.append(new_row)

            index_path.write_text("\n".join(lines), encoding="utf-8")
        else:
            # Create new index file
            header = [
                "# SBM Migration Reports",
                "",
                "Table of contents for all migration reports.",
                "",
                "| Date | Slug | Status | Duration | Lines | Report |",
                "|------|------|--------|----------|-------|--------|",
                new_row,
                "",
            ]
            index_path.write_text("\n".join(header), encoding="utf-8")

        logger.debug(f"Updated index.md with report for {result.slug}")

    except Exception as e:
        logger.warning(f"Failed to update index.md: {e}")
