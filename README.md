# SCAC Data Collection

This repository contains scaffolding for collecting securities class action filings from the [Stanford Securities Class Action Clearinghouse (SCAC)](https://securities.stanford.edu/). The first step in the research workflow is to gather structured filings metadata that can later be combined with insider-trading datasets for machine learning experiments.

## Getting Started

1. **Install dependencies**
   ```bash
   poetry install
   ```
2. **Review the site policies** � read Stanford's usage guidelines and respect the `robots.txt`. Only proceed if your intended use is permitted.
3. **Prepare credentials** � the SCAC site exposes JSON endpoints but enforces authentication for full pagination. Export credentials as environment variables to avoid hard-coding secrets:
   ```powershell
   setx SCAC_EMAIL "your-email"
   setx SCAC_PASSWORD "your-password"
   ```
4. **Choose a polite User-Agent** � update `src/scac/client.py` with a User-Agent string that includes accurate contact information for your project.

## Collecting Filings

The helper script `scripts/collect_filings.py` downloads filings data and can output to either CSV or JSON format:

### CSV Format (Recommended)

Saves data with columns: Filing Name, Filing Date, District Court, Exchange, Ticker

```bash
# Collect basic data without HTML scraping (faster, safer)
poetry run python scripts/collect_filings.py --skip-details --max-pages 10 --output data/filings.csv --sleep 1

# Collect complete data with court names, exchange, and ticker (slower, scrapes HTML)
poetry run python scripts/collect_filings.py --max-pages 5 --output data/filings.csv --sleep 2

# Collect all available pages
poetry run python scripts/collect_filings.py --output data/filings.csv --sleep 2
```

### JSON Lines Format

Saves raw data with all fields:

```bash
poetry run python scripts/collect_filings.py --max-pages 5 --output data/filings.jsonl --sleep 1
```

### Key Options:
- `--max-pages` - Caps pagination while you verify behavior (default: unlimited)
- `--skip-details` - Skip fetching HTML details to avoid rate limiting (court will show as ID)
- `--sleep` - Seconds to pause between requests (default: 2.0s)
- `--output` - Output file path (.csv or .jsonl format based on extension)

### Important Notes:
- **Rate Limiting:** The script scrapes individual case HTML pages to get court names, exchange, and ticker data. Use `--sleep 2` or higher to avoid account suspension.
- **Without `--skip-details`:** Fetches HTML for each case (30 requests per page + 1 page request)
- **With `--skip-details`:** Only fetches page data (1 request per page) - much faster and safer
- **Authentication Required:** Script needs valid credentials for pagination beyond the first page

If you run the script without credentials it will still retrieve the first page but stops when pagination appears locked by the server.

## Data Sources

The script uses multiple endpoints to collect complete data:

### JSON API Endpoints
- `POST /filings.json` - Returns tabular filings metadata (`foundset` with 30 rows per page)
- `GET /filings-case.json?id=<cld_id>` - Returns detailed attributes for a single case
- `POST /login.json` - Authenticates the session using form fields `email`, `pass`, `remember`, `referer`, `returnTo`

### HTML Scraping
- `GET /filings-case.php?id=<cld_id>` - Individual case pages containing:
  - **District Court** name (e.g., "S.D. New York")
  - **Exchange/Market** information (e.g., "NASDAQ", "New York SE")
  - **Ticker Symbol** (e.g., "AAPL", "MSFT")

The JSON responses embed JavaScript date strings (e.g. `"new Date(1753686000000)"`). The client normalizes these to ISO-8601 timestamps before writing to disk.

## Next Steps

- Validate pagination after authenticating (the public session only returns page 1).
- Extend the crawler with retry/backoff logic once the site behaviour is confirmed.
- Join the filings data with insider trading datasets (e.g., Form 4 filings) and begin feature engineering for the machine learning component of the paper.
