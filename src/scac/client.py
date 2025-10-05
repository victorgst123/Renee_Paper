"""Client for interacting with the Stanford Securities Class Action Clearinghouse (SCAC)."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional
from urllib.parse import urljoin

import requests
from requests import Response, Session

_LOGGER = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": "ReneePaperResearchBot/0.1 (rliu42@hawk.illinoistech.edu)",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

_DATE_PATTERN = re.compile(r"^new Date\((\d+)\)$")


class SCACLoginError(RuntimeError):
    """Raised when login fails."""


@dataclass
class LoginResult:
    success: bool
    errors: Optional[Dict[str, Any]] = None
    redirect: Optional[str] = None


class SCACClient:
    """Thin HTTP client around the semi-documented SCAC JSON endpoints."""

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        *,
        base_url: str = "https://securities.stanford.edu/",
        session: Optional[Session] = None,
        timeout: int = 15,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.email = email
        self.password = password
        self.timeout = timeout
        self.session = session or requests.Session()
        merged_headers = dict(_DEFAULT_HEADERS)
        if headers:
            merged_headers.update(headers)
        self.session.headers.update(merged_headers)

    def _url(self, path: str) -> str:
        return urljoin(self.base_url, path)

    def _get(self, path: str, **kwargs: Any) -> Response:
        response = self.session.get(self._url(path), timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response

    def _post(self, path: str, **kwargs: Any) -> Response:
        response = self.session.post(self._url(path), timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response

    def bootstrap(self) -> None:
        """Prime the session with initial cookies."""
        self._get("index.html")

    def login(self, email: Optional[str] = None, password: Optional[str] = None) -> LoginResult:
        payload_email = email or self.email
        payload_password = password or self.password
        if not payload_email or not payload_password:
            raise ValueError("Email and password must be provided for login")

        self.bootstrap()
        payload = {
            "email": payload_email,
            "pass": payload_password,
            "remember": 0,
            "referer": "index",
            "returnTo": "",
        }
        response = self._post("login.json", data=payload)
        result = response.json()
        success = bool(result.get("success")) or bool(result.get("redirect"))
        errors = result.get("errors")
        login_result = LoginResult(success=success, errors=errors, redirect=result.get("redirect"))

        if not login_result.success:
            _LOGGER.error("Login failed: %s", errors or result)
            raise SCACLoginError(f"SCAC login failed: {errors or result}")

        return login_result

    def fetch_filings_page(
        self,
        page: int = 1,
        *,
        params: Optional[Dict[str, Any]] = None,
        method: str = "post",
    ) -> Dict[str, Any]:
        """Retrieve a page from filings.json.

        The endpoint appears to require POST requests for pagination when authenticated.
        When unauthenticated the server currently responds with the first page only.
        """
        form: Dict[str, Any] = {"page": page, "ajax": "true"}
        if params:
            form.update(params)

        if method.lower() == "get":
            response = self._get("filings.json", params=form)
        else:
            response = self._post("filings.json", data=form)
        payload = response.json()
        return payload

    def iter_filings(
        self,
        *,
        params: Optional[Dict[str, Any]] = None,
        max_pages: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Stream filings across pages."""
        page = 1
        seen_ids: set[int] = set()
        while True:
            payload = self.fetch_filings_page(page=page, params=params)
            foundset: List[Dict[str, Any]] = payload.get("foundset", [])
            if not foundset:
                break

            for record in foundset:
                record_id = record.get("cld_id")
                if record_id in seen_ids:
                    continue
                if record_id is not None:
                    seen_ids.add(record_id)
                yield record

            pagination = payload.get("pagination", {})
            current = pagination.get("current", page)
            last = pagination.get("last", page)
            if max_pages is not None and page >= max_pages:
                break
            if page >= last:
                break
            if current == page:
                page += 1
            else:
                page = current + 1

    def fetch_case_detail(self, cld_id: int) -> Dict[str, Any]:
        """Fetch metadata for an individual case via filings-case.json."""
        response = self._get(f"filings-case.json", params={"id": cld_id})
        payload = response.json()
        record = payload.get("record")
        if not record:
            raise RuntimeError(f"Case detail not returned for cld_id={cld_id}")
        return record

    def fetch_case_details_from_html(self, cld_id: int) -> Dict[str, str]:
        """Fetch case details from HTML page to get court, exchange, and ticker.

        Returns:
            Dictionary with keys: court, exchange, ticker
        """
        import re

        response = self._get(f"filings-case.php", params={"id": cld_id})
        html = response.text

        details = {
            "court": "",
            "exchange": "",
            "ticker": ""
        }

        # Extract court
        court_match = re.search(r'<strong>COURT:</strong>\s*([^<]+)', html, re.IGNORECASE)
        if court_match:
            details["court"] = court_match.group(1).strip()

        # Extract exchange/market
        market_match = re.search(r'<strong>Company Market:</strong>\s*([^<]+)', html, re.IGNORECASE)
        if market_match:
            details["exchange"] = market_match.group(1).strip()

        # Extract ticker
        ticker_match = re.search(r'<strong>Ticker Symbol:</strong>\s*([^<]+)', html, re.IGNORECASE)
        if ticker_match:
            details["ticker"] = ticker_match.group(1).strip()

        return details

    def perform_advanced_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform an advanced search with specified criteria.

        Args:
            params: Search parameters including:
                - filing_year_from: Starting year
                - filing_year_to: Ending year
                - claims[]: Claim type (e.g., "1934 act claims - section 10b")

        Returns:
            Search results as a dictionary with foundset and pagination.
        """
        _LOGGER.info("Performing advanced search with parameters: %s", params)
        # Add required ajax parameter
        search_data = {"ajax": "true", "page": 1}
        search_data.update(params)

        # Try GET request first - some forms use GET for search
        response = self._get("filings.json", params=search_data)
        payload = response.json()

        # Debug: log a sample record to see what we got
        if payload.get("foundset"):
            _LOGGER.debug("Sample record: %s", payload["foundset"][0])

        return payload

    @staticmethod
    def normalize_dates(record: Dict[str, Any]) -> Dict[str, Any]:
        """Convert SCAC's JS-style date strings into ISO-8601 timestamps."""
        normalised: Dict[str, Any] = {}
        for key, value in record.items():
            normalised[key] = _normalize_value(value)
        return normalised


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        match = _DATE_PATTERN.match(value)
        if match:
            milliseconds = int(match.group(1))
            dt = datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc)
            return dt.isoformat()
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def dump_json(records: Iterable[Dict[str, Any]]) -> str:
    """Helper to serialise records with normalised dates."""
    normalised = [SCACClient.normalize_dates(record) for record in records]
    return json.dumps(normalised, indent=2, sort_keys=True, ensure_ascii=True)
