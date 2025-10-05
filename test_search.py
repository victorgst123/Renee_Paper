#!/usr/bin/env python
"""Test script to debug search parameters."""
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
print("Logged in successfully")

# Test 1: No filters (should get latest results)
print("\n=== Test 1: No filters ===")
resp1 = client.session.post(
    "https://securities.stanford.edu/filings.json",
    data={"ajax": "true", "page": 1}
)
result1 = resp1.json()
if result1.get("foundset"):
    print(f"Count: {len(result1['foundset'])}")
    print(f"First year: {result1['foundset'][0].get('cld_filing_year')}")

# Test 2: Try year filter with yearFrom/yearTo
print("\n=== Test 2: yearFrom=2001, yearTo=2001 ===")
resp2 = client.session.post(
    "https://securities.stanford.edu/filings.json",
    data={"ajax": "true", "page": 1, "yearFrom": "2001", "yearTo": "2001"}
)
result2 = resp2.json()
if result2.get("foundset"):
    print(f"Count: {len(result2['foundset'])}")
    print(f"First year: {result2['foundset'][0].get('cld_filing_year')}")

# Test 3: Try with claims filter
print("\n=== Test 3: claims[] filter ===")
resp3 = client.session.post(
    "https://securities.stanford.edu/filings.json",
    data={
        "ajax": "true",
        "page": 1,
        "claims[]": "1934 act claims - section 10b"
    }
)
result3 = resp3.json()
if result3.get("foundset"):
    print(f"Count: {len(result3['foundset'])}")
    print(f"Last page: {result3.get('pagination', {}).get('last')}")
    print(f"First year: {result3['foundset'][0].get('cld_filing_year')}")

# Test 4: Try submitting to search endpoint first
print("\n=== Test 4: Submit search first, then get results ===")
# Submit the search
search_resp = client.session.post(
    "https://securities.stanford.edu/filings-search.json",
    data={
        "yearFrom": "2001",
        "yearTo": "2001",
        "claims[]": "1934 act claims - section 10b"
    }
)
print(f"Search submission status: {search_resp.status_code}")
if search_resp.status_code == 200:
    try:
        search_result = search_resp.json()
        print(f"Search result: {search_result}")
    except:
        print(f"Search response (first 200 chars): {search_resp.text[:200]}")

# Now try to get filtered results
resp4 = client.session.post(
    "https://securities.stanford.edu/filings.json",
    data={"ajax": "true", "page": 1}
)
result4 = resp4.json()
if result4.get("foundset"):
    print(f"Count: {len(result4['foundset'])}")
    print(f"First year: {result4['foundset'][0].get('cld_filing_year')}")
