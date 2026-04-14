"""Exchange calendar and DST-aware scheduling utilities.

Provides:
  1. Holiday calendars for JPX (Tokyo), LSE (London), and NYSE (New York).
  2. A helper to check whether a given exchange is open on a given date.
  3. DST-offset computation so agents can detect when cron-based ET
     schedules are misaligned with the actual exchange local time.

Holiday dates are maintained as static lists for the current and next
calendar year.  Update annually or replace with an API-based source
(e.g. exchangecalendar, pandas_market_calendars) for full automation.

DST rules:
  - U.S. (ET/EDT): 2nd Sunday in March → 1st Sunday in November
  - UK  (GMT/BST): Last Sunday in March → Last Sunday in October
  - Japan (JST):   No DST — always UTC+9
"""
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# ── Timezone constants ─────────────────────────────────────

TZ_ET = ZoneInfo("America/New_York")
TZ_LONDON = ZoneInfo("Europe/London")
TZ_TOKYO = ZoneInfo("Asia/Tokyo")


# ── Holiday calendars ──────────────────────────────────────
# Keyed by year.  Each list contains (month, day) tuples.
# Sources: JPX, LSE, NYSE official calendars.
# Update these annually or swap in pandas_market_calendars for automation.

_NYSE_HOLIDAYS: dict[int, list[tuple[int, int]]] = {
    2026: [
        (1, 1),   # New Year's Day
        (1, 19),  # MLK Day
        (2, 16),  # Presidents' Day
        (4, 3),   # Good Friday
        (5, 25),  # Memorial Day
        (7, 3),   # Independence Day (observed)
        (9, 7),   # Labor Day
        (11, 26), # Thanksgiving
        (12, 25), # Christmas
    ],
    2027: [
        (1, 1),   # New Year's Day
        (1, 18),  # MLK Day
        (2, 15),  # Presidents' Day
        (3, 26),  # Good Friday
        (5, 31),  # Memorial Day
        (7, 5),   # Independence Day (observed)
        (9, 6),   # Labor Day
        (11, 25), # Thanksgiving
        (12, 24), # Christmas (observed)
    ],
}

_LSE_HOLIDAYS: dict[int, list[tuple[int, int]]] = {
    2026: [
        (1, 1),   # New Year's Day
        (4, 3),   # Good Friday
        (4, 6),   # Easter Monday
        (5, 4),   # Early May Bank Holiday
        (5, 25),  # Spring Bank Holiday
        (8, 31),  # Summer Bank Holiday
        (12, 25), # Christmas
        (12, 28), # Boxing Day (observed)
    ],
    2027: [
        (1, 1),   # New Year's Day
        (3, 26),  # Good Friday
        (3, 29),  # Easter Monday
        (5, 3),   # Early May Bank Holiday
        (5, 31),  # Spring Bank Holiday
        (8, 30),  # Summer Bank Holiday
        (12, 27), # Christmas (observed)
        (12, 28), # Boxing Day (observed)
    ],
}

_JPX_HOLIDAYS: dict[int, list[tuple[int, int]]] = {
    2026: [
        (1, 1),   # New Year's Day
        (1, 2),   # Bank Holiday
        (1, 3),   # Bank Holiday
        (1, 12),  # Coming of Age Day
        (2, 11),  # National Foundation Day
        (2, 23),  # Emperor's Birthday
        (3, 20),  # Vernal Equinox Day
        (4, 29),  # Showa Day
        (5, 3),   # Constitution Memorial Day
        (5, 4),   # Greenery Day
        (5, 5),   # Children's Day
        (5, 6),   # Substitute Holiday
        (7, 20),  # Marine Day
        (8, 11),  # Mountain Day
        (9, 21),  # Respect for the Aged Day
        (9, 23),  # Autumnal Equinox Day
        (10, 12), # Sports Day
        (11, 3),  # Culture Day
        (11, 23), # Labor Thanksgiving Day
        (12, 31), # Bank Holiday
    ],
    2027: [
        (1, 1),   # New Year's Day
        (1, 2),   # Bank Holiday
        (1, 3),   # Bank Holiday
        (1, 11),  # Coming of Age Day
        (2, 11),  # National Foundation Day
        (2, 23),  # Emperor's Birthday
        (3, 21),  # Vernal Equinox Day (approx)
        (4, 29),  # Showa Day
        (5, 3),   # Constitution Memorial Day
        (5, 4),   # Greenery Day
        (5, 5),   # Children's Day
        (7, 19),  # Marine Day
        (8, 11),  # Mountain Day
        (9, 20),  # Respect for the Aged Day
        (9, 23),  # Autumnal Equinox Day
        (10, 11), # Sports Day
        (11, 3),  # Culture Day
        (11, 23), # Labor Thanksgiving Day
        (12, 31), # Bank Holiday
    ],
}

EXCHANGE_HOLIDAYS: dict[str, dict[int, list[tuple[int, int]]]] = {
    "NYSE": _NYSE_HOLIDAYS,
    "LSE": _LSE_HOLIDAYS,
    "JPX": _JPX_HOLIDAYS,
}


def is_exchange_holiday(exchange: str, d: date | None = None) -> bool:
    """Check whether *d* (default: today in ET) is a holiday for *exchange*.

    Args:
        exchange: One of "NYSE", "LSE", "JPX".
        d: The date to check.  Defaults to today in America/New_York.

    Returns:
        True if the exchange is closed for a holiday on that date.
    """
    if d is None:
        d = datetime.now(TZ_ET).date()
    holidays = EXCHANGE_HOLIDAYS.get(exchange, {}).get(d.year, [])
    return (d.month, d.day) in holidays


def is_exchange_open(exchange: str, d: date | None = None) -> bool:
    """Return True if *exchange* is expected to be open on *d*.

    Checks both weekends and known holidays.  Does not account for
    emergency closures or half-days.
    """
    if d is None:
        d = datetime.now(TZ_ET).date()
    # Weekends (Mon=0 … Sun=6)
    if d.weekday() >= 5:
        return False
    # JPX also closes on Saturdays/Sundays (same weekday convention)
    return not is_exchange_holiday(exchange, d)


# ── DST offset utilities ──────────────────────────────────

def get_utc_offset_hours(tz: ZoneInfo, dt: datetime | None = None) -> float:
    """Return the current UTC offset in hours for *tz*."""
    if dt is None:
        dt = datetime.now(tz)
    else:
        dt = dt.astimezone(tz)
    offset = dt.utcoffset()
    if offset is None:
        return 0.0
    return offset.total_seconds() / 3600


def get_et_offset_to(target_tz: ZoneInfo, dt: datetime | None = None) -> float:
    """Return the offset in hours from ET to *target_tz* at time *dt*.

    Positive means target_tz is ahead of ET.
    Example: Tokyo is normally ET+14 in winter, ET+13 in summer (U.S. EDT).
    """
    if dt is None:
        dt = datetime.now(TZ_ET)
    et_offset = get_utc_offset_hours(TZ_ET, dt)
    target_offset = get_utc_offset_hours(target_tz, dt)
    return target_offset - et_offset


def is_dst_transition_week() -> dict[str, bool]:
    """Check whether we are within ±7 days of a DST transition for U.S. or UK.

    Returns a dict like {"US": True, "UK": False} indicating whether
    the ET-based cron schedules may be misaligned with the actual
    exchange local time.  Japan never has DST transitions.
    """
    now = datetime.now(TZ_ET)
    result: dict[str, bool] = {"US": False, "UK": False}

    for label, tz in [("US", TZ_ET), ("UK", TZ_LONDON)]:
        # Check if the UTC offset changes within ±7 days
        offsets = set()
        for delta_days in range(-7, 8):
            check = now + timedelta(days=delta_days)
            offsets.add(get_utc_offset_hours(tz, check))
        if len(offsets) > 1:
            result[label] = True

    return result


def get_schedule_drift_warning() -> str | None:
    """Return a human-readable warning if DST transitions may affect schedules.

    Returns None if no transitions are imminent.
    """
    transitions = is_dst_transition_week()
    warnings = []

    if transitions["US"]:
        warnings.append(
            "U.S. DST transition within ±7 days — ET-based cron schedules "
            "for Nikkei monitors may be off by 1 hour relative to Tokyo time."
        )
    if transitions["UK"]:
        warnings.append(
            "UK DST (BST) transition within ±7 days — ET-based cron schedules "
            "for FTSE monitors may be off by 1 hour relative to London time."
        )

    if not warnings:
        return None
    return " | ".join(warnings)


def get_current_session_info() -> dict:
    """Return a snapshot of current exchange session status and DST info.

    Useful for logging and the API status endpoint.
    """
    now_et = datetime.now(TZ_ET)
    today = now_et.date()

    return {
        "timestamp_et": now_et.isoformat(),
        "exchanges": {
            "NYSE": {
                "open_today": is_exchange_open("NYSE", today),
                "holiday": is_exchange_holiday("NYSE", today),
            },
            "LSE": {
                "open_today": is_exchange_open("LSE", today),
                "holiday": is_exchange_holiday("LSE", today),
            },
            "JPX": {
                "open_today": is_exchange_open("JPX", today),
                "holiday": is_exchange_holiday("JPX", today),
            },
        },
        "dst": {
            "et_utc_offset": get_utc_offset_hours(TZ_ET, now_et),
            "london_utc_offset": get_utc_offset_hours(TZ_LONDON, now_et),
            "tokyo_utc_offset": get_utc_offset_hours(TZ_TOKYO, now_et),
            "et_to_tokyo_hours": get_et_offset_to(TZ_TOKYO, now_et),
            "et_to_london_hours": get_et_offset_to(TZ_LONDON, now_et),
            "transition_warning": get_schedule_drift_warning(),
        },
    }
