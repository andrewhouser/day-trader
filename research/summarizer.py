"""Report summarizer — generates human-readable market briefs from MarketReport data.

Uses the LLM (via the existing call_ollama) for narrative synthesis, or falls back
to a template-based summary if the LLM is unavailable.
"""
from __future__ import annotations

import logging
from datetime import datetime

from research.models import MarketReport, NarrativeCluster, NormalizedItem

logger = logging.getLogger(__name__)

SUMMARIZER_SYSTEM = (
    "You are a senior market analyst producing a concise, evidence-backed market brief. "
    "Distinguish macro from company-specific causes. Include both US and international context. "
    "Cite sources. Be specific with data. Avoid speculation beyond what the evidence supports."
)


def generate_human_summary(report: MarketReport) -> str:
    """Generate a human-readable summary from a MarketReport.

    Tries LLM first; falls back to template if LLM is unavailable.
    """
    try:
        return _llm_summary(report)
    except Exception as e:
        logger.warning(f"LLM summary failed, using template: {e}")
        return _template_summary(report)


def _llm_summary(report: MarketReport) -> str:
    """Use the LLM to synthesize a polished market brief."""
    from agent import call_ollama
    import config

    # Build context from report data
    narrative_block = ""
    for i, cluster in enumerate(report.top_narratives[:8], 1):
        sources = ", ".join({item.source for item in cluster.items})
        narrative_block += (
            f"{i}. {cluster.label}\n"
            f"   Sentiment: {cluster.aggregate_sentiment.value} | "
            f"Influence: {cluster.influence_score} | "
            f"Confidence: {cluster.confidence}\n"
            f"   Affected: {', '.join(cluster.affected_assets[:5]) or 'broad market'}\n"
            f"   Regions: {', '.join(cluster.regions[:5])}\n"
            f"   Sources: {sources}\n"
            f"   Items: {len(cluster.items)}\n\n"
        )

    macro_block = ""
    for item in report.top_macro_releases[:5]:
        macro_block += f"- [{item.source}] {item.title}: {item.summary}\n"

    filings_block = ""
    for item in report.top_company_catalysts[:5]:
        filings_block += f"- [{item.source}] {item.title}: {item.summary}\n"

    prompt = f"""Market Research Brief — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Based on the following multi-source research data, produce a concise market brief.

### Top Market Narratives
{narrative_block or "No significant narratives detected."}

### Key Macro Data
{macro_block or "No macro releases in this cycle."}

### Notable Filings / Company Catalysts
{filings_block or "No notable filings."}

### Risk Factors
{chr(10).join(f'- {r}' for r in report.risk_factors) or "None identified."}

### Bullish Factors
{chr(10).join(f'- {b}' for b in report.bullish_factors) or "None identified."}

### Bearish Factors
{chr(10).join(f'- {b}' for b in report.bearish_factors) or "None identified."}

---

Write a structured brief with these sections:
1. **Executive Summary** (3-4 sentences: what is driving markets right now)
2. **US Market View** (key influences on SPY/QQQ/DIA)
3. **International View** (Europe, Japan, emerging markets, FX, commodities)
4. **Top Narratives** (ranked list of the most important market stories)
5. **Risk Assessment** (what could go wrong, what to watch)
6. **Data Sources** (list the sources used and note any that were unavailable)

Prioritize primary sources (FRED, BLS, SEC, central banks) over commentary.
If primary and secondary sources conflict, note the discrepancy.
Total items analyzed: {len(report.all_items)}"""

    response = call_ollama(prompt, system=SUMMARIZER_SYSTEM, model=config.RESEARCH_MODEL, timeout=config.RESEARCH_TIMEOUT)
    return response


def _template_summary(report: MarketReport) -> str:
    """Fallback template-based summary when LLM is unavailable."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Market Research Brief — {now}",
        f"",
        f"Items analyzed: {len(report.all_items)} | "
        f"Narratives: {len(report.top_narratives)} | "
        f"Scope: {report.market_scope}",
        "",
        "## Top Narratives",
    ]

    for i, cluster in enumerate(report.top_narratives[:8], 1):
        sources = ", ".join({item.source for item in cluster.items})
        lines.append(
            f"{i}. **{cluster.label}** — "
            f"{cluster.aggregate_sentiment.value} "
            f"(influence: {cluster.influence_score}, "
            f"confidence: {cluster.confidence})\n"
            f"   Sources: {sources} | "
            f"Assets: {', '.join(cluster.affected_assets[:5]) or 'broad'} | "
            f"Regions: {', '.join(cluster.regions[:3])}"
        )

    if report.top_macro_releases:
        lines.append("\n## Key Macro Data")
        for item in report.top_macro_releases[:5]:
            lines.append(f"- [{item.source}] {item.summary}")

    if report.top_company_catalysts:
        lines.append("\n## Notable Filings")
        for item in report.top_company_catalysts[:5]:
            lines.append(f"- [{item.source}] {item.summary}")

    if report.risk_factors:
        lines.append("\n## Risk Factors")
        for r in report.risk_factors:
            lines.append(f"- {r}")

    if report.bullish_factors:
        lines.append("\n## Bullish Factors")
        for b in report.bullish_factors:
            lines.append(f"- {b}")

    if report.bearish_factors:
        lines.append("\n## Bearish Factors")
        for b in report.bearish_factors:
            lines.append(f"- {b}")

    return "\n".join(lines)
