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

# Fetch case page
resp = client.session.get("https://securities.stanford.edu/filings-case.php?id=108640")
with open("case_108640.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

print(f"Saved case page to case_108640.html ({len(resp.text)} bytes)")

# Also check main filings page table structure
resp2 = client.session.get("https://securities.stanford.edu/filings.html")
with open("filings_table.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)

print(f"Saved filings page to filings_table.html ({len(resp2.text)} bytes)")
