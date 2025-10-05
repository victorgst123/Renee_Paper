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

The helper script `scripts/collect_filings.py` downloads filings and (optionally) case-level details:

```bash
poetry run python scripts/collect_filings.py --max-pages 5 --with-details --output data/filings.jsonl
```

Key options:
- `--max-pages` caps pagination while you verify behaviour.
- `--with-details` fetches `filings-case.json?id=<cld_id>` for each row.
- `--sleep` throttles requests between pages (default 0.5s).

If you run the script without credentials it will still retrieve the first page but stops when pagination appears locked by the server.

## JSON Endpoints Observed

- `GET /filings.json` � returns tabular filings metadata (`foundset` with 30 rows per page).
- `GET /filings-case.json?id=<cld_id>` � returns detailed attributes for a single case.
- `POST /login.json` � authenticates the session using form fields `email`, `pass`, `remember`, `referer`, `returnTo`.

The responses embed JavaScript date strings (e.g. `"new Date(1753686000000)"`). The client normalises these to ISO-8601 timestamps before writing to disk.

## Next Steps

- Validate pagination after authenticating (the public session only returns page 1).
- Extend the crawler with retry/backoff logic once the site behaviour is confirmed.
- Join the filings data with insider trading datasets (e.g., Form 4 filings) and begin feature engineering for the machine learning component of the paper.
