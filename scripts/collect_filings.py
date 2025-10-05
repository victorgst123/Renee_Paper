"""Utility script to pull filings data from the SCAC site.

Note: Review and comply with Stanford's Terms of Use before running this script.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scac.client import SCACClient, SCACLoginError

_LOGGER = logging.getLogger(__name__)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download filings data from SCAC")
    parser.add_argument("--email", default=os.getenv("SCAC_EMAIL"), help="Account email")
    parser.add_argument("--password", default=os.getenv("SCAC_PASSWORD"), help="Account password")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/filings.jsonl"),
        help="Destination file (JSON lines)",
    )
    parser.add_argument("--max-pages", type=int, default=1, help="Maximum filings pages to retrieve")
    parser.add_argument(
        "--with-details",
        action="store_true",
        help="Fetch filings-case.json for each cld_id and embed under case_detail",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="Seconds to pause between page requests to stay polite",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(message)s")

    if not args.email or not args.password:
        _LOGGER.warning("No credentials provided; pagination beyond the first page may be blocked by SCAC")

    client = SCACClient(email=args.email, password=args.password)

    if args.email and args.password:
        try:
            client.login()
            _LOGGER.info("Successfully logged in")
        except (SCACLoginError, ValueError) as exc:
            _LOGGER.error("Unable to authenticate: %s", exc)
            return 1
    else:
        client.bootstrap()

    # Navigate to the main filings database page
    _LOGGER.info("Navigating to Securities Class Action Clearinghouse: Filings Database")

    # Save the data to output file
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Determine output format based on file extension
    if args.output.suffix.lower() == '.csv':
        # Save as CSV with columns: Filing Name, Filing Date, District Court, Exchange, Ticker
        with args.output.open("w", encoding="utf-8", newline='') as fp:
            csv_writer = csv.writer(fp)
            # Write header
            csv_writer.writerow(["Filing Name", "Filing Date", "District Court", "Exchange", "Ticker"])

            # Iterate through pages
            page = 1
            total_records = 0
            seen_pages = set()

            while True:
                _LOGGER.info("Fetching page %d...", page)
                results = client.fetch_filings_page(page=page)

                foundset = results.get("foundset", [])
                pagination = results.get("pagination", {})

                raw_current = pagination.get("current", page)
                try:
                    current = int(raw_current)
                except (TypeError, ValueError):
                    current = page

                if current in seen_pages:
                    _LOGGER.warning("Stopping on page %s; server returned duplicate pagination value", current)
                    break
                seen_pages.add(current)

                if not foundset:
                    _LOGGER.info("No records returned for page %s; stopping", current)
                    break

                _LOGGER.info("Processing page %s with %s records", current, len(foundset))

                for record in foundset:
                    filing_name = record.get("composite_litigation_name", "")
                    filing_date = record.get("cld_fic_filing_long_date", "")

                    # Get court, exchange, and ticker from HTML case page
                    cld_id = record.get("cld_id")
                    district_court = ""
                    exchange = ""
                    ticker = ""

                    if cld_id:
                        try:
                            case_details = client.fetch_case_details_from_html(cld_id)
                            district_court = case_details.get("court", "")
                            exchange = case_details.get("exchange", "")
                            ticker = case_details.get("ticker", "")
                            _LOGGER.debug("Fetched details for %s: %s", filing_name, case_details)
                        except Exception as e:
                            _LOGGER.warning("Failed to fetch HTML details for CLD ID %s: %s", cld_id, e)
                            # Fallback to court_lut_id if HTML fetch fails
                            district_court = str(record.get("courts_lut_id", ""))

                    csv_writer.writerow([filing_name, filing_date, district_court, exchange, ticker])
                    total_records += 1

                    # Sleep between requests to be polite
                    if args.sleep > 0:
                        time.sleep(args.sleep)

                # Check if we've reached max pages
                if args.max_pages and len(seen_pages) >= args.max_pages:
                    _LOGGER.info("Reached max pages limit (%d)", args.max_pages)
                    break

                # Check if this is the last page
                last_page = pagination.get("last")
                try:
                    last_page_int = int(last_page) if last_page is not None else None
                except (TypeError, ValueError):
                    last_page_int = None

                if last_page_int is not None and current >= last_page_int:
                    _LOGGER.info("Reached server-reported last page (%s)", last_page_int)
                    break

                page = current + 1

        _LOGGER.info("=" * 80)
        _LOGGER.info("Saved %d total records to CSV file: %s", total_records, args.output)
        _LOGGER.info("=" * 80)
    else:
        # Save as JSON Lines (existing code for multi-page)
        total_records = 0
        page = 1
        seen_pages = set()

        with args.output.open("w", encoding="utf-8") as fp:
            while True:
                _LOGGER.info("Fetching page %d...", page)
                results = client.fetch_filings_page(page=page)

                foundset = results.get("foundset", [])
                pagination = results.get("pagination", {})

                raw_current = pagination.get("current", page)
                try:
                    current = int(raw_current)
                except (TypeError, ValueError):
                    current = page

                if current in seen_pages:
                    _LOGGER.warning("Stopping on page %s; server returned duplicate pagination value", current)
                    break
                seen_pages.add(current)

                if not foundset:
                    _LOGGER.info("No records returned for page %s; stopping", current)
                    break

                _LOGGER.info("Processing page %s with %s records", current, len(foundset))

                for record in foundset:
                    normalized = client.normalize_dates(record)
                    fp.write(json.dumps(normalized, ensure_ascii=False) + "\n")
                    total_records += 1

                if args.max_pages and len(seen_pages) >= args.max_pages:
                    _LOGGER.info("Reached max pages limit (%d)", args.max_pages)
                    break

                last_page = pagination.get("last")
                try:
                    last_page_int = int(last_page) if last_page is not None else None
                except (TypeError, ValueError):
                    last_page_int = None

                if last_page_int is not None and current >= last_page_int:
                    _LOGGER.info("Reached server-reported last page (%s)", last_page_int)
                    break

                page = current + 1
                if args.sleep > 0:
                    time.sleep(args.sleep)

        _LOGGER.info("=" * 80)
        _LOGGER.info("Saved %d total records to %s", total_records, args.output)
        _LOGGER.info("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
