"""
Market hours / trading-day utilities for IST.
NSE: 09:15 – 15:30 IST, Monday–Friday.
"""
from datetime import datetime, timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")

# Hard-coded list of NSE 2025-2026 holidays (subset; trading-day check is
# best-effort — TTL bridges any miss).
NSE_HOLIDAYS_2025 = {
    "2025-01-26", "2025-02-26", "2025-03-14", "2025-03-31", "2025-04-10",
    "2025-04-14", "2025-04-18", "2025-05-01", "2025-08-15", "2025-08-27",
    "2025-10-02", "2025-10-21", "2025-11-05", "2025-12-25",
}
NSE_HOLIDAYS_2026 = {
    "2026-01-26", "2026-03-03", "2026-03-19", "2026-04-03", "2026-05-01",
    "2026-08-15", "2026-08-26", "2026-10-02", "2026-11-09", "2026-12-25",
}
NSE_HOLIDAYS = NSE_HOLIDAYS_2025 | NSE_HOLIDAYS_2026


def now_ist() -> datetime:
    return datetime.now(IST)


def is_trading_day(dt: datetime = None) -> bool:
    dt = dt or now_ist()
    if dt.weekday() >= 5:  # Sat/Sun
        return False
    if dt.strftime("%Y-%m-%d") in NSE_HOLIDAYS:
        return False
    return True


def is_market_open(dt: datetime = None) -> bool:
    dt = dt or now_ist()
    if not is_trading_day(dt):
        return False
    open_t = dt.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = dt.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= dt <= close_t


def trading_days_between(d1: datetime, d2: datetime) -> int:
    """Count trading days between two timestamps (rough)."""
    if d1 > d2:
        d1, d2 = d2, d1
    days = 0
    cur = d1
    while cur < d2:
        if is_trading_day(cur):
            days += 1
        cur += timedelta(days=1)
    return days


def stale_threshold_days() -> int:
    """How old can closing data be before we reject it?
    > 4 days bridges Fri-close → Mon-open + 1 holiday safely.
    """
    return 4
