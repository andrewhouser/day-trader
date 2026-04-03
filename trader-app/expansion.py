"""Portfolio expansion proposals — suggest, approve, and manage new instruments.

The research agent proposes new instruments (stocks, bonds, etc.) for portfolio
expansion. Proposals require explicit user approval before the trader can execute
against them. Approved instruments are added to the runtime INSTRUMENTS config
and persisted to disk so they survive restarts.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import config
from agent import call_ollama

logger = logging.getLogger(__name__)

PROPOSALS_PATH = os.path.join(config.DATA_DIR, "expansion_proposals.json")
APPROVED_INSTRUMENTS_PATH = os.path.join(config.DATA_DIR, "approved_instruments.json")


class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def _load_proposals() -> list[dict]:
    try:
        with open(PROPOSALS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_proposals(proposals: list[dict]):
    with open(PROPOSALS_PATH, "w") as f:
        json.dump(proposals, f, indent=2, default=str)


def _load_approved_instruments() -> dict[str, dict]:
    try:
        with open(APPROVED_INSTRUMENTS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_approved_instruments(instruments: dict[str, dict]):
    with open(APPROVED_INSTRUMENTS_PATH, "w") as f:
        json.dump(instruments, f, indent=2)


def load_approved_into_config():
    """Load user-approved instruments into the runtime config.INSTRUMENTS.
    Called at startup so the trader can trade them immediately."""
    approved = _load_approved_instruments()
    for ticker, info in approved.items():
        if ticker not in config.INSTRUMENTS:
            config.INSTRUMENTS[ticker] = info
            logger.info(f"Loaded approved instrument into config: {ticker}")


def get_proposals(status: Optional[str] = None) -> list[dict]:
    """Return proposals, optionally filtered by status."""
    proposals = _load_proposals()
    if status:
        proposals = [p for p in proposals if p.get("status") == status]
    return proposals


def get_proposal(proposal_id: str) -> Optional[dict]:
    proposals = _load_proposals()
    for p in proposals:
        if p["id"] == proposal_id:
            return p
    return None


def approve_proposal(proposal_id: str) -> Optional[dict]:
    """Approve a proposal — adds the instrument to the tradeable set."""
    proposals = _load_proposals()
    target = None
    for p in proposals:
        if p["id"] == proposal_id:
            target = p
            break

    if not target:
        return None
    if target["status"] != ProposalStatus.PENDING:
        return target  # already decided

    target["status"] = ProposalStatus.APPROVED
    target["decided_at"] = datetime.now().isoformat()
    _save_proposals(proposals)

    # Add to approved instruments and runtime config
    ticker = target["ticker"]
    instrument_info = {
        "type": target.get("instrument_type", "Stock"),
        "tracks": target.get("description", ticker),
    }

    approved = _load_approved_instruments()
    approved[ticker] = instrument_info
    _save_approved_instruments(approved)

    config.INSTRUMENTS[ticker] = instrument_info
    logger.info(f"Approved expansion: {ticker} — now tradeable")

    return target


def reject_proposal(proposal_id: str, reason: str = "") -> Optional[dict]:
    """Reject a proposal."""
    proposals = _load_proposals()
    target = None
    for p in proposals:
        if p["id"] == proposal_id:
            target = p
            break

    if not target:
        return None
    if target["status"] != ProposalStatus.PENDING:
        return target

    target["status"] = ProposalStatus.REJECTED
    target["decided_at"] = datetime.now().isoformat()
    target["rejection_reason"] = reason
    _save_proposals(proposals)

    logger.info(f"Rejected expansion: {target['ticker']} — reason: {reason}")
    return target


def create_proposal(
    ticker: str,
    instrument_type: str,
    description: str,
    rationale: str,
    category: str = "stock",
    region: str = "US",
    risk_level: str = "moderate",
    expected_return: str = "",
    source: str = "research_agent",
) -> dict:
    """Create a new expansion proposal."""
    proposal = {
        "id": uuid.uuid4().hex[:12],
        "ticker": ticker.upper(),
        "instrument_type": instrument_type,
        "description": description,
        "category": category,
        "region": region,
        "risk_level": risk_level,
        "expected_return": expected_return,
        "rationale": rationale,
        "source": source,
        "status": ProposalStatus.PENDING,
        "created_at": datetime.now().isoformat(),
        "decided_at": None,
        "rejection_reason": None,
    }

    proposals = _load_proposals()

    # Don't duplicate — if same ticker is already pending, skip
    for existing in proposals:
        if existing["ticker"] == proposal["ticker"] and existing["status"] == ProposalStatus.PENDING:
            logger.info(f"Proposal for {ticker} already pending — skipping")
            return existing

    proposals.append(proposal)
    _save_proposals(proposals)
    logger.info(f"Created expansion proposal: {ticker} ({instrument_type}) — {category}")
    return proposal


EXPANSION_SYSTEM = (
    "You are a portfolio expansion analyst. Your job is to identify instruments "
    "beyond the current ETF-only portfolio that could improve returns through "
    "diversification into individual stocks, bonds, REITs, or other vehicles. "
    "Be specific with ticker symbols, instrument types, and rationale. "
    "Focus on risk-adjusted returns and income growth potential. "
    "Only suggest instruments that are liquid and tradeable on major US exchanges."
)


def run_expansion_analysis() -> str:
    """Run the expansion analysis — uses the LLM to suggest new instruments
    based on current portfolio, market conditions, and research data."""
    from agent import load_portfolio, read_recent_entries
    from market_data import get_market_summary

    logger.info("Starting portfolio expansion analysis...")

    portfolio = load_portfolio()
    market_summary = get_market_summary()
    recent_research = read_recent_entries(config.RESEARCH_PATH, 5)

    # Get current instrument list (including any already approved)
    current_tickers = list(config.INSTRUMENTS.keys())
    current_positions = [p["ticker"] for p in portfolio["positions"]]

    # Get existing pending/approved proposals to avoid re-suggesting
    existing_proposals = _load_proposals()
    already_proposed = [
        p["ticker"] for p in existing_proposals
        if p["status"] in (ProposalStatus.PENDING, ProposalStatus.APPROVED)
    ]

    prompt = f"""Portfolio Expansion Analysis

You manage a paper trading portfolio currently limited to these instruments:
{json.dumps(current_tickers)}

Current positions: {json.dumps(current_positions) if current_positions else "None (all cash)"}
Portfolio value: ${portfolio['total_value_usd']:.2f}
Cash available: ${portfolio['cash_usd']:.2f}

Already proposed (do not re-suggest): {json.dumps(already_proposed) if already_proposed else "None"}

{market_summary}

### Recent Research Context
{recent_research[:3000] if recent_research else "No recent research available."}

---

Analyze the current market environment and suggest 3-5 new instruments that could
improve portfolio returns through diversification. Consider:

1. **Individual Stocks** — high-quality companies with strong fundamentals,
   earnings momentum, or sector tailwinds
2. **Bond ETFs or Treasury instruments** — for income and risk management
   (e.g., TLT, BND, HYG, TIPS)
3. **REITs** — for real estate exposure and dividend income
4. **Sector ETFs** — for targeted sector exposure beyond broad market
5. **International instruments** — for geographic diversification
6. **Commodity exposure** — gold, silver, or commodity ETFs if conditions warrant

For EACH suggestion, provide a JSON block:

```json
{{
  "ticker": "AAPL",
  "instrument_type": "Stock",
  "description": "Apple Inc. — technology hardware and services",
  "category": "stock",
  "region": "US",
  "risk_level": "moderate",
  "expected_return": "8-12% annually based on earnings growth",
  "rationale": "Strong services revenue growth, massive buyback program, AI catalyst..."
}}
```

Valid categories: stock, bond, reit, sector_etf, international, commodity, other
Valid risk levels: low, moderate, high
Valid instrument types: Stock, Bond ETF, REIT, Sector ETF, International ETF, Commodity ETF, Treasury ETF

Be specific about WHY each instrument makes sense given current market conditions.
Consider the portfolio's current ETF-heavy composition and suggest instruments
that complement rather than duplicate existing exposure."""

    logger.info("Sending expansion analysis prompt to LLM...")
    response = call_ollama(prompt, system=EXPANSION_SYSTEM, model=config.RESEARCH_MODEL)
    logger.info(f"Expansion analysis received ({len(response)} chars)")

    # Parse proposals from the response
    import re
    json_pattern = r'```json\s*(.*?)\s*```'
    matches = re.findall(json_pattern, response, re.DOTALL)

    created = []
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict) and "ticker" in data:
                proposal = create_proposal(
                    ticker=data["ticker"],
                    instrument_type=data.get("instrument_type", "Stock"),
                    description=data.get("description", ""),
                    rationale=data.get("rationale", ""),
                    category=data.get("category", "stock"),
                    region=data.get("region", "US"),
                    risk_level=data.get("risk_level", "moderate"),
                    expected_return=data.get("expected_return", ""),
                    source="research_agent",
                )
                created.append(proposal)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse expansion proposal: {e}")

    logger.info(f"Created {len(created)} expansion proposals")

    # Save the full analysis to research log
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    from agent import append_to_file
    entry = f"""
## Portfolio Expansion Analysis - {timestamp}

{response}

**Proposals created:** {len(created)}
{chr(10).join(f"- {p['ticker']}: {p['description']}" for p in created)}

---
"""
    append_to_file(config.RESEARCH_PATH, entry)

    return response
