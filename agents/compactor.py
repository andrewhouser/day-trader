"""Memory compaction agent for the day-trader.

Reduces filesystem bloat in research.md, trade_log.md, and reflections.md
while retaining historical context through summarized archives.

New files produced:
  - research_history.md  — daily research digests
  - trade_history.md     — monthly trade roll-ups
  - lessons.md           — distilled trading lessons
"""
import logging
import os
import re
from datetime import datetime, timedelta

import config
from agents.agent import append_to_file, call_ollama

logger = logging.getLogger(__name__)

COMPACTION_SYSTEM = (
    "You are a concise financial analyst assistant. "
    "Your job is to summarize trading data accurately. "
    "Preserve all numbers, dates, tickers, and key insights. "
    "Be brief but complete — nothing important should be lost."
)


# ── Helpers ────────────────────────────────────────────────

def _read_file(path: str) -> str:
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _write_file(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)


def _ensure_file(path: str, header: str):
    """Create a file with a header if it doesn't exist."""
    if not os.path.exists(path):
        _write_file(path, header)


def _split_entries(content: str) -> tuple[str, list[str]]:
    """Split a markdown log into (header, [entries]).
    Entries are separated by '---' lines."""
    sections = content.split("\n---\n")
    header = sections[0] if sections else ""
    entries = [s.strip() for s in sections[1:] if s.strip()]
    return header, entries


def _extract_date_from_entry(entry: str) -> datetime | None:
    """Try to pull a date from a log entry (various formats)."""
    patterns = [
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, entry)
        if m:
            raw = m.group(1)
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(raw, fmt)
                except ValueError:
                    continue
    return None


# ── Research Compaction ────────────────────────────────────

def compact_research() -> dict:
    """Compact research.md: summarize old entries into a daily digest,
    archive to research_history.md, keep only recent entries."""
    logger.info("Compacting research.md ...")
    content = _read_file(config.RESEARCH_PATH)
    if not content.strip():
        logger.info("research.md is empty, nothing to compact.")
        return {"status": "skipped", "reason": "empty"}

    header, entries = _split_entries(content)
    keep = config.RESEARCH_KEEP_ENTRIES

    if len(entries) <= keep:
        logger.info(f"Only {len(entries)} entries, below threshold of {keep}. Skipping.")
        return {"status": "skipped", "reason": "below_threshold", "entries": len(entries)}

    old_entries = entries[:-keep]
    recent_entries = entries[-keep:]

    # Group old entries by date
    by_date: dict[str, list[str]] = {}
    for entry in old_entries:
        dt = _extract_date_from_entry(entry)
        key = dt.strftime("%Y-%m-%d") if dt else "unknown"
        by_date.setdefault(key, []).append(entry)

    # Summarize each day's research into a digest
    _ensure_file(
        config.RESEARCH_HISTORY_PATH,
        "# Research History\n\nDaily digests of compacted research notes.\n\n---\n",
    )

    digests_created = 0
    for date_key, day_entries in sorted(by_date.items()):
        combined = "\n\n---\n\n".join(day_entries)
        prompt = f"""Summarize the following {len(day_entries)} research notes from {date_key}
into a single concise daily digest. Preserve:
- Market regime assessment (bull/bear/sideways)
- Key instrument levels and trends
- Notable thesis shifts during the day
- Final watchlist and trigger levels

Research notes:
{combined}

Write the digest as a compact markdown section. No preamble."""

        digest = call_ollama(prompt, system=COMPACTION_SYSTEM, model=config.COMPACTION_MODEL)

        digest_entry = f"""
## Daily Digest — {date_key}

{digest}

---
"""
        append_to_file(config.RESEARCH_HISTORY_PATH, digest_entry)
        digests_created += 1

    # Truncate research.md to header + recent entries
    new_content = header + "\n---\n" + "\n---\n".join(recent_entries) + "\n---\n"
    _write_file(config.RESEARCH_PATH, new_content)

    result = {
        "status": "compacted",
        "entries_removed": len(old_entries),
        "entries_kept": len(recent_entries),
        "digests_created": digests_created,
    }
    logger.info(f"Research compaction complete: {result}")
    return result


# ── Trade Log Compaction ───────────────────────────────────

def compact_trade_log() -> dict:
    """Compact trade_log.md: roll up entries older than retention period
    into monthly summaries in trade_history.md."""
    logger.info("Compacting trade_log.md ...")
    content = _read_file(config.TRADE_LOG_PATH)
    if not content.strip():
        logger.info("trade_log.md is empty, nothing to compact.")
        return {"status": "skipped", "reason": "empty"}

    header, entries = _split_entries(content)
    cutoff = datetime.now() - timedelta(days=config.TRADE_LOG_RETENTION_DAYS)

    old_entries = []
    recent_entries = []
    for entry in entries:
        dt = _extract_date_from_entry(entry)
        if dt and dt < cutoff:
            old_entries.append(entry)
        else:
            recent_entries.append(entry)

    if not old_entries:
        logger.info("No trade entries older than retention period. Skipping.")
        return {"status": "skipped", "reason": "nothing_old", "entries": len(entries)}

    # Group old entries by month
    by_month: dict[str, list[str]] = {}
    for entry in old_entries:
        dt = _extract_date_from_entry(entry)
        key = dt.strftime("%Y-%m") if dt else "unknown"
        by_month.setdefault(key, []).append(entry)

    _ensure_file(
        config.TRADE_HISTORY_PATH,
        "# Trade History\n\nMonthly roll-ups of compacted trade log entries.\n\n---\n",
    )

    months_created = 0
    for month_key, month_entries in sorted(by_month.items()):
        combined = "\n\n---\n\n".join(month_entries)
        prompt = f"""Summarize the following {len(month_entries)} trades from {month_key}
into a monthly trade summary. Include:
- Total number of trades (buys and sells separately)
- Win/loss count and win rate
- Net realized P&L
- Most traded instruments
- Notable trades (best win, worst loss)
- Brief pattern observations

Trade entries:
{combined}

Write as a compact markdown section. No preamble."""

        summary = call_ollama(prompt, system=COMPACTION_SYSTEM, model=config.COMPACTION_MODEL)

        summary_entry = f"""
## Monthly Summary — {month_key}

{summary}

---
"""
        append_to_file(config.TRADE_HISTORY_PATH, summary_entry)
        months_created += 1

    # Truncate trade_log.md to header + recent entries
    new_content = header + "\n---\n"
    if recent_entries:
        new_content += "\n---\n".join(recent_entries) + "\n---\n"
    _write_file(config.TRADE_LOG_PATH, new_content)

    result = {
        "status": "compacted",
        "entries_removed": len(old_entries),
        "entries_kept": len(recent_entries),
        "months_created": months_created,
    }
    logger.info(f"Trade log compaction complete: {result}")
    return result


# ── Reflections Compaction ─────────────────────────────────

def compact_reflections() -> dict:
    """Compact reflections.md: distill old reflections into durable lessons
    in lessons.md, deduplicating against existing lessons."""
    logger.info("Compacting reflections.md ...")
    content = _read_file(config.REFLECTIONS_PATH)
    if not content.strip():
        logger.info("reflections.md is empty, nothing to compact.")
        return {"status": "skipped", "reason": "empty"}

    header, entries = _split_entries(content)
    cutoff = datetime.now() - timedelta(days=config.REFLECTIONS_RETENTION_DAYS)

    old_entries = []
    recent_entries = []
    for entry in entries:
        dt = _extract_date_from_entry(entry)
        if dt and dt < cutoff:
            old_entries.append(entry)
        else:
            recent_entries.append(entry)

    if not old_entries:
        logger.info("No reflections older than retention period. Skipping.")
        return {"status": "skipped", "reason": "nothing_old", "entries": len(entries)}

    _ensure_file(
        config.LESSONS_PATH,
        "# Trading Lessons\n\nDistilled lessons from past reflections. Updated by the compaction agent.\n\n---\n",
    )

    existing_lessons = _read_file(config.LESSONS_PATH)
    combined = "\n\n---\n\n".join(old_entries)

    prompt = f"""You are reviewing {len(old_entries)} trading reflections to extract durable lessons.

Existing lessons (do NOT repeat these):
{existing_lessons}

New reflections to distill:
{combined}

Extract new, non-redundant lessons. Each lesson should be:
- A concise, actionable insight (1-2 sentences)
- Grounded in specific patterns observed in the reflections
- Formatted as a bullet point starting with "- "

If all lessons are already captured in the existing file, respond with exactly: NO_NEW_LESSONS

Otherwise, list only the new lessons. No preamble or explanation."""

    response = call_ollama(prompt, system=COMPACTION_SYSTEM, model=config.COMPACTION_MODEL)

    new_lessons = 0
    if "NO_NEW_LESSONS" not in response.upper():
        lesson_entry = f"""
## Lessons extracted — {datetime.now().strftime('%Y-%m-%d')}

{response.strip()}

---
"""
        append_to_file(config.LESSONS_PATH, lesson_entry)
        new_lessons = response.strip().count("\n- ") + (1 if response.strip().startswith("- ") else 0)

    # Truncate reflections.md to header + recent entries
    new_content = header + "\n---\n"
    if recent_entries:
        new_content += "\n---\n".join(recent_entries) + "\n---\n"
    _write_file(config.REFLECTIONS_PATH, new_content)

    result = {
        "status": "compacted",
        "entries_removed": len(old_entries),
        "entries_kept": len(recent_entries),
        "new_lessons": new_lessons,
    }
    logger.info(f"Reflections compaction complete: {result}")
    return result


# ── Main Entry Point ───────────────────────────────────────

def run_compaction() -> dict:
    """Run full compaction cycle across all files."""
    logger.info("=" * 50)
    logger.info("Starting memory compaction cycle")
    logger.info("=" * 50)

    results = {
        "timestamp": datetime.now().isoformat(),
        "research": compact_research(),
        "trade_log": compact_trade_log(),
        "reflections": compact_reflections(),
    }

    logger.info(f"Compaction cycle complete: {results}")
    return results
