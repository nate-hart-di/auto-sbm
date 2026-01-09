#!/usr/bin/env python3
"""
Script to retrieve dealer slugs from account names using devtools search.

This script reads a list of dealer account names from an Excel or CSV file,
uses 'devtools search' to find the corresponding slug for each dealer,
and writes the results to a formatted slugs.txt file.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import click

# Optional imports for Excel support
try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class SlugRetriever:
    """Retrieve dealer slugs from account names."""

    def __init__(self, input_file: Path, output_file: Path) -> None:
        """
        Initialize the slug retriever.

        Args:
            input_file: Path to input file (Excel or CSV)
            output_file: Path to output slugs.txt file
        """
        self.input_file = input_file
        self.output_file = output_file
        self.results: list[dict[str, str]] = []

    def read_input_file(self) -> list[str]:
        """
        Read website URLs or account names from input file.

        Returns:
            List of search terms (website domains or account names)

        Raises:
            ValueError: If file format is not supported or pandas is not available
        """
        file_ext = self.input_file.suffix.lower()

        if file_ext == ".csv":
            return self._read_csv()
        if file_ext in [".xlsx", ".xls"]:
            if not PANDAS_AVAILABLE:
                msg = (
                    "pandas is required for Excel files. Install with: pip install pandas openpyxl"
                )
                raise ValueError(msg)
            return self._read_excel()

        msg = f"Unsupported file format: {file_ext}. Supported formats: .csv, .xlsx, .xls"
        raise ValueError(msg)

    def _read_csv(self) -> list[str]:
        """Read website URLs from CSV file, filtering by Stage column."""
        import csv
        from urllib.parse import urlparse

        websites = []
        seen_urls = set()  # Track duplicates

        with self.input_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                msg = "CSV file has no headers"
                raise ValueError(msg)

            # Look for website URL column (Salesforce format)
            url_columns = [
                "Account: Website",
                "Website",
                "website",
                "URL",
                "url",
                "prod",
            ]
            url_col = None
            for col in url_columns:
                if col in reader.fieldnames:
                    url_col = col
                    click.echo(f"  Using column: {url_col}")
                    break

            if not url_col:
                msg = "Could not find website URL column in CSV"
                raise ValueError(msg)

            # Look for Stage column (Salesforce format) for filtering
            stage_columns = [
                "Stage",
                "stage",
                "Status",
                "status",
            ]
            stage_col = None
            for col in stage_columns:
                if col in reader.fieldnames:
                    stage_col = col
                    click.echo(f"  Filtering by column: {stage_col}")
                    break

            skipped_count = 0
            for row in reader:
                # Filter by stage if column exists - only include "Mockup Approved"
                if stage_col:
                    stage = row.get(stage_col, "").strip()
                    if "Mockup Approved" not in stage:
                        skipped_count += 1
                        continue

                url = row.get(url_col, "").strip()
                if url:
                    # Extract domain from URL (e.g., "https://www.lexusofcoloradosprings.com/" -> "www.lexusofcoloradosprings.com")
                    parsed = urlparse(url)
                    domain = (
                        parsed.netloc or parsed.path.split("/")[0]
                    )  # Handle URLs with or without scheme
                    domain = domain.strip("/")

                    if domain and domain not in seen_urls:
                        websites.append(domain)
                        seen_urls.add(domain)

            if skipped_count > 0:
                click.echo(f"  ⏭️  Skipped {skipped_count} rows (not in 'Mockup Approved' stage)")

        return websites

    def _read_excel(self) -> list[str]:
        """Read account names from Excel file."""
        if not PANDAS_AVAILABLE or pd is None:
            msg = "pandas is required for Excel files"
            raise ValueError(msg)

        # Try reading with default header first
        df = pd.read_excel(self.input_file)

        # If columns are all "Unnamed" or mostly NaN, try to find header row
        if all(col.startswith("Unnamed") for col in df.columns) or df.dropna(how="all").empty:
            click.echo("  Detecting Salesforce report format, scanning for header row...")

            # Read without header to find actual header row
            df_raw = pd.read_excel(self.input_file, header=None)

            # Find header row (look for row with multiple non-null values that look like headers)
            for i in range(min(20, len(df_raw))):  # Check first 20 rows
                row = df_raw.iloc[i].dropna()
                if len(row) >= 3 and any(
                    "Account" in str(val) or "Name" in str(val) for val in row
                ):
                    # Found potential header row
                    click.echo(f"  Found header row at row {i}")
                    df = pd.read_excel(self.input_file, header=i)
                    break

        # Try common column name patterns (including Salesforce format)
        name_columns = [
            "Account: Account Name",
            "Account Name",
            "account_name",
            "name",
            "Name",
            "Dealer Name",
            "dealer_name",
        ]
        name_col = None
        for col in name_columns:
            if col in df.columns:
                name_col = col
                click.echo(f"  Using column: {name_col}")
                break

        if not name_col:
            # Use first non-empty column
            for col in df.columns:
                if df[col].notna().any():
                    name_col = col
                    click.echo(
                        f"⚠️  No standard name column found. Using first non-empty column: {name_col}"
                    )
                    break

        if name_col is None:
            msg = "Could not find any column with data in Excel file"
            raise ValueError(msg)

        # Get non-null account names and deduplicate
        all_names = df[name_col].dropna().astype(str).str.strip().tolist()

        # Filter out empty strings and deduplicate while preserving order
        account_names = []
        seen_names = set()
        for name in all_names:
            # Normalize common character encoding issues
            name = name.replace("?", "'")  # Fix common apostrophe encoding issue
            if name and name not in seen_names:
                account_names.append(name)
                seen_names.add(name)

        return account_names

    def search_slug(self, search_term: str) -> tuple[str, dict] | None:
        """
        Search for slug using devtools search command.

        Args:
            search_term: The website domain or account name to search for

        Returns:
            Tuple of (slug, dealer_data) if found, None otherwise
        """
        # Path to main devtools script
        devtools_cli_dir = Path(
            "/Users/nathanhart/code/dealerinspire/feature-dev-shared-scripts/devtools-cli"
        )
        devtools_script = devtools_cli_dir / "devtools"

        if not devtools_script.exists():
            logger.error(f"devtools script not found at: {devtools_script}")
            logger.error("Please check the path or ensure devtools-cli is cloned.")
            sys.exit(1)

        try:
            # Execute devtools search command
            # The devtools script handles all the necessary environment setup
            result = subprocess.run(
                ["bash", str(devtools_script), "search", search_term],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(devtools_cli_dir),
            )

            if result.returncode != 0:
                logger.warning(f"devtools search failed for '{search_term}': {result.stderr}")
                return None

            # Parse JSON output
            try:
                output = result.stdout.strip()
                if not output:
                    logger.warning(f"Empty output from devtools search for '{search_term}'")
                    return None

                # Remove ANSI color codes and filter to just JSON
                # The first line often has colored text, so we need to find the JSON array
                lines = output.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    # Remove ANSI escape codes
                    clean_line = re.sub(r"\x1b\[[0-9;]*m", "", line)
                    # Start collecting when we see opening bracket
                    if clean_line.strip().startswith("[") or clean_line.strip().startswith("{"):
                        in_json = True
                    if in_json:
                        json_lines.append(clean_line)

                if not json_lines:
                    logger.warning(f"No JSON found in devtools output for '{search_term}'")
                    logger.debug(f"Output was: {output[:200]}")
                    return None

                json_str = "\n".join(json_lines)
                data = json.loads(json_str)

                # Check if no results found
                if isinstance(data, dict) and "message" in data:
                    logger.debug(f"No match found: {data['message']}")
                    return None

                # data should be a list of dealers
                if not isinstance(data, list) or len(data) == 0:
                    logger.warning(f"No results found for '{search_term}'")
                    return None

                # When searching by website domain, should get exactly 1 result
                # When searching by name, need exact match
                if len(data) == 1:
                    dealer_data = data[0]
                    slug = dealer_data.get("slug")
                    logger.info(f"Match found: '{search_term}' -> {slug}")
                    return (slug, dealer_data)

                # Multiple results - try exact name match (for backwards compat with name-based search)
                search_lower = search_term.lower().strip()
                for result_item in data:
                    result_name_lower = result_item.get("name", "").lower().strip()
                    if result_name_lower == search_lower:
                        # Found exact match
                        dealer_data = result_item
                        slug = dealer_data.get("slug")
                        logger.info(f"Exact match found: '{search_term}' -> {slug}")
                        return (slug, dealer_data)

                # No exact match found - log and skip
                names = [r.get("name") for r in data[:3]]  # Show first 3
                logger.warning(
                    f"No exact match for '{search_term}'. "
                    f"Found {len(data)} partial matches: {names}"
                )
                return None

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON output for '{search_term}': {e}")
                logger.debug(f"Output was: {result.stdout[:200]}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"devtools search timed out for '{search_term}'")
            return None
        except Exception as e:
            logger.error(f"Error searching for '{search_term}': {e}")
            return None

    def _find_best_match(self, search_name: str, results: list[dict]) -> dict | None:
        """
        Find the best matching dealer from multiple results.

        Args:
            search_name: The name being searched for
            results: List of dealer dictionaries from devtools search

        Returns:
            The best matching dealer dict, or None
        """
        if not results:
            return None

        search_lower = search_name.lower()

        # First, try exact match (case-insensitive)
        for result in results:
            if result.get("name", "").lower() == search_lower:
                return result

        # Next, try exact match in slug
        search_slug_normalized = re.sub(r"[^a-z0-9-]", "-", search_lower)
        for result in results:
            if result.get("slug", "") == search_slug_normalized:
                return result

        # Finally, find the result with the most similar name
        best_match = None
        best_score = 0

        for result in results:
            name = result.get("name", "").lower()
            # Simple similarity: count matching words
            search_words = set(search_lower.split())
            name_words = set(name.split())
            common_words = search_words.intersection(name_words)
            score = len(common_words)

            if score > best_score:
                best_score = score
                best_match = result

        return best_match if best_score > 0 else results[0]

    def retrieve_all_slugs(self, search_terms: list[str]) -> None:
        """
        Retrieve slugs for all search terms (websites or account names).

        Args:
            search_terms: List of website domains or account names to search
        """
        total = len(search_terms)
        click.echo(f"\n🔍 Searching for {total} dealer slugs...")

        for i, search_term in enumerate(search_terms, 1):
            click.echo(f"  [{i}/{total}] Searching: {search_term}")

            result = self.search_slug(search_term)

            if result:
                slug, dealer_data = result
                self.results.append(
                    {
                        "search_term": search_term,
                        "slug": slug,
                        "dealer_data": dealer_data,
                        "status": "found",
                    }
                )
                click.echo(f"    ✅ Found: {slug}")
            else:
                self.results.append({"search_term": search_term, "slug": "", "status": "not_found"})
                click.echo(f"    ❌ Not found")

    def write_output_file(self) -> None:
        """Write results to output file in JSON format matching devtools search output."""
        # Build JSON array matching devtools format
        output_data = []
        seen_slugs = set()

        for result in self.results:
            if result["status"] == "found" and result.get("dealer_data"):
                slug = result["dealer_data"].get("slug")
                # Only add if we haven't seen this slug yet (avoid duplicates)
                if slug and slug not in seen_slugs:
                    output_data.append(result["dealer_data"])
                    seen_slugs.add(slug)

        # Write JSON to file
        with self.output_file.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
            f.write("\n")  # Add trailing newline

        # Write slugs.txt with ONLY unique slugs, one per line
        txt_file = self.output_file.parent / "slugs.txt"
        with txt_file.open("w", encoding="utf-8") as f:
            # Write only unique slugs, one per line, no comments
            unique_slugs = []
            for result in self.results:
                if result["status"] == "found" and result["slug"]:
                    if result["slug"] not in unique_slugs:
                        unique_slugs.append(result["slug"])

            for slug in unique_slugs:
                f.write(f"{slug}\n")

    def print_summary(self) -> None:
        """Print summary of results."""
        found = sum(1 for r in self.results if r["status"] == "found")
        not_found = sum(1 for r in self.results if r["status"] == "not_found")

        click.echo("\n" + "=" * 60)
        click.echo("📊 Summary")
        click.echo("=" * 60)
        click.echo(f"Total dealers processed: {len(self.results)}")
        click.echo(f"✅ Slugs found: {found}")
        click.echo(f"❌ Slugs not found: {not_found}")
        click.echo(f"📄 Output file: {self.output_file}")
        click.echo("=" * 60)


@click.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: slugs.json in auto-sbm directory)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(input_file: Path, output: Path | None, verbose: bool) -> None:
    """
    Retrieve dealer slugs from account names using devtools search.

    INPUT_FILE: Path to Excel (.xlsx, .xls) or CSV (.csv) file containing dealer account names.

    The file should have a column named "Account Name", "name", or similar.
    If not found, the first column will be used.

    Output: JSON file matching devtools search format with dealer data.

    Examples:
        sbm get-slugs /path/to/dealers.xlsx
        sbm get-slugs /path/to/dealers.csv --output custom-slugs.json
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Determine output file
    if output is None:
        # Default to slugs.json in data directory
        repo_root = Path(__file__).parent.parent
        data_dir = repo_root / "data"
        data_dir.mkdir(exist_ok=True)
        output = data_dir / "slugs.json"

    click.echo("🚀 Dealer Slug Retriever")
    click.echo(f"📂 Input file: {input_file}")
    click.echo(f"📝 Output file: {output}")

    # Check if pandas is available for Excel files
    if input_file.suffix.lower() in [".xlsx", ".xls"] and not PANDAS_AVAILABLE:
        click.echo("❌ Error: pandas is required for Excel files")
        click.echo("Install with: pip install pandas openpyxl")
        sys.exit(1)

    try:
        retriever = SlugRetriever(input_file, output)

        # Read input file
        click.echo("\n📖 Reading input file...")
        search_terms = retriever.read_input_file()
        click.echo(f"✅ Found {len(search_terms)} websites")

        # Retrieve slugs
        retriever.retrieve_all_slugs(search_terms)

        # Write output
        click.echo(f"\n💾 Writing results to {output}...")
        retriever.write_output_file()
        click.echo("✅ Output file written")

        # Print summary
        retriever.print_summary()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if verbose:
            logger.exception("Detailed error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
