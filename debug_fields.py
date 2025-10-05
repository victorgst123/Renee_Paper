#!/usr/bin/env python
"""Debug script to explore available data fields."""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from scac.client import SCACClient

client = SCACClient(
    email=os.getenv("SCAC_EMAIL"),
    password=os.getenv("SCAC_PASSWORD")
)

client.login()
print("Logged in successfully\n")

# Fetch first page
results = client.fetch_filings_page(page=1)
foundset = results.get('foundset', [])

if foundset:
    first_record = foundset[0]
    print("=" * 80)
    print("ALL FIELDS IN FIRST RECORD:")
    print("=" * 80)
    for key in sorted(first_record.keys()):
        value = first_record[key]
        if isinstance(value, str) and len(value) > 100:
            value = value[:100] + "..."
        print(f"{key:40s} = {value}")

# Try to fetch case detail
print("\n" + "=" * 80)
print("CASE DETAIL FOR CLD_ID 108640:")
print("=" * 80)

try:
    detail = client.fetch_case_detail(108640)
    for key in sorted(detail.keys()):
        value = detail[key]
        if isinstance(value, str) and len(value) > 100:
            value = value[:100] + "..."
        print(f"{key:40s} = {value}")
except Exception as e:
    print(f"Error fetching case detail: {e}")

# Also check the HTML page structure
print("\n" + "=" * 80)
print("CHECKING HTML PAGE:")
print("=" * 80)

resp = client.session.get("https://securities.stanford.edu/filings.html")
# Look for the first table row of data
import re
# Find table rows
rows = re.findall(r'<tr[^>]*class="[^"]*case-row[^"]*"[^>]*>(.*?)</tr>', resp.text, re.DOTALL)[:1]
if rows:
    print("First data row HTML (first 500 chars):")
    print(rows[0][:500])
