"""SEC EDGAR adapter — recent filings from the SEC full-text search API.

No API key required. Uses the public EDGAR EFTS (full-text search) and
company filings endpoints. Rate limit: 10 req/sec with User-Agent header.
https://efts.sec.gov/LATEST/search-index?q=...
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import requests

from research.models import NormalizedItem, SourceCategory, SourceType
from research.adapters.base import SourceAdapter

logger = logging.getLogger(__name__)

EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FILINGS = "https://data.sec.gov/submissions"
EDGAR_FULL_TEXT = "https://efts.sec.gov/LATEST/search-index"

# CIKs for major ETF issuers / companies we track
TRACKED_CIKS = {
    "0000036377": "SPY (State Street)",
    "0001067983": "Berkshire Hathaway",
    "0000320193": "Apple Inc.",
    "0000789019": "Microsoft Corp.",
    "0001045810": "NVIDIA Corp.",
}

# Filing types of interest
FILING_TYPES = ["8-K", "10-Q", "10-K", "S-1", "DEF 14A"]


class SecEdgarAdapter(SourceAdapter):
    source_key = "sec_edgar"

    def __init__(self, search_terms: list[str] | None = None):
        super().__init__()
        self.search_terms = search_terms or [
            "earnings", "guidance", "restructuring", "dividend",
            "stock buyback", "merger", "acquisition",
        ]
        self._session = requests.Session()
        contact = os.getenv("SEC_EDGAR_CONTACT", "research-agent@example.com")
        self._session.headers["User-Agent"] = f"TraderResearchAgent/1.0 ({contact})"

    def fetch(self) -> list[dict]:
        results = []
        today = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")

        # Use EDGAR full-text search for recent filings
        for term in self.search_terms[:4]:  # limit queries
            try:
                resp = self._session.get(
                    "https://efts.sec.gov/LATEST/search-index",
                    params={
                        "q": term,
                        "dateRange": "custom",
                        "startdt": start,
                        "enddt": today,
                        "forms": ",".join(FILING_TYPES),
                    },
                    timeout=15,
                )
                if resp.status_code == 429:
                    logger.warning("[sec_edgar] rate limited")
                    break
                resp.raise_for_status()
                data = resp.json()
                hits = data.get("hits", {}).get("hits", [])
                for hit in hits[:5]:
                    src = hit.get("_source", {})
                    src["_search_term"] = term
                    results.append(src)
            except Exception as e:
                logger.error(f"[sec_edgar] search error for '{term}': {e}")

        return results

    def parse(self, raw: list[dict]) -> list[dict]:
        parsed = []
        seen = set()
        for item in raw:
            accession = item.get("file_num", "") or item.get("accession_no", "")
            if accession in seen:
                continue
            seen.add(accession)

            parsed.append({
                "company": item.get("display_names", [item.get("entity_name", "Unknown")])[0]
                    if item.get("display_names") else item.get("entity_name", "Unknown"),
                "form_type": item.get("form_type", ""),
                "filed_date": item.get("file_date", ""),
                "accession": accession,
                "description": item.get("file_description", ""),
                "search_term": item.get("_search_term", ""),
            })
        return parsed

    def normalize(self, parsed: list[dict]) -> list[NormalizedItem]:
        items = []
        for p in parsed:
            pub = None
            try:
                pub = datetime.strptime(p["filed_date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass

            title = f"SEC {p['form_type']}: {p['company']}"
            summary = p.get("description", "") or f"{p['form_type']} filing by {p['company']}"
            if p.get("search_term"):
                summary += f" (matched: {p['search_term']})"

            items.append(NormalizedItem(
                title=title,
                summary=summary,
                source="sec_edgar",
                category=SourceCategory.FILINGS,
                source_type=SourceType.PRIMARY,
                published_at=pub,
                url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum={p['accession']}&type=&dateb=&owner=include&count=10",
                symbols=[],
                regions=["US"],
                themes=["filings", p.get("search_term", "")],
                raw_payload=p,
            ))
        return items
