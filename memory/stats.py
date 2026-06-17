"""Pure-function statistics aggregation over memory records.

This module contains :func:`aggregate_statistics`, a side-effect-free
function that turns a list of memory record dicts (as returned by
:meth:`memory.manager.MemoryManager.list_memory`) into a
:class:`memory.types.MemoryStatistics` payload suitable for charts and
metrics.

Keeping the aggregation logic separate from :class:`MemoryManager` makes
it trivial to unit-test without mocking mem0, and lets the UI compute
statistics from already-fetched data without an extra round-trip.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from memory.types import (
    CategoryStat,
    DailyCountStat,
    MemoryRecord,
    MemoryStatistics,
    TagStat,
)

# Number of days covered by the daily-counts series.
DAILY_WINDOW_DAYS: int = 30

# Sentinel used when a memory has no category metadata.
UNCATEGORIZED: str = "uncategorized"


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO timestamp string into a timezone-aware datetime.

    Handles both trailing-``Z`` and explicit-offset forms. Returns ``None``
    when the input is empty or cannot be parsed.

    Args:
        value: The ISO timestamp string (or ``None``).

    Returns:
        A timezone-aware :class:`datetime`, or ``None``.
    """
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    # Normalize trailing Z to +00:00 for fromisoformat compatibility.
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _extract_category(memory: MemoryRecord) -> str:
    """Return the category name for a memory, or the uncategorized sentinel.

    Args:
        memory: The memory record dict.

    Returns:
        The category string (never ``None``).
    """
    metadata = memory.get("metadata") or {}
    category = metadata.get("category") or metadata.get("type")
    if not category:
        return UNCATEGORIZED
    return str(category)


def _extract_tags(memory: MemoryRecord) -> list[str]:
    """Return the list of tags for a memory.

    Tags may be stored under ``metadata.tags`` as a list or a
    comma-separated string. Missing/invalid tags yield an empty list.

    Args:
        memory: The memory record dict.

    Returns:
        A list of tag strings.
    """
    metadata = memory.get("metadata") or {}
    raw = metadata.get("tags")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(tag).strip() for tag in raw if str(tag).strip()]
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    return []


def _build_daily_counts(
    memories: list[MemoryRecord],
    today: datetime,
) -> list[DailyCountStat]:
    """Build a 30-day daily count series ending today.

    Args:
        memories: The memory record list.
        today: The reference "now" (timezone-aware).

    Returns:
        A list of :class:`DailyCountStat` entries, oldest first.
    """
    # Initialize the window with zero counts.
    start = (today - timedelta(days=DAILY_WINDOW_DAYS - 1)).date()
    date_to_counts: dict[str, int] = {}
    for offset in range(DAILY_WINDOW_DAYS):
        day = start + timedelta(days=offset)
        date_to_counts[day.isoformat()] = 0

    # Tally memories by creation date.
    for memory in memories:
        created = _parse_timestamp(memory.get("created_at"))
        if created is None:
            continue
        day_key = created.astimezone(UTC).date().isoformat()
        if day_key in date_to_counts:
            date_to_counts[day_key] += 1

    return [
        {"date": day_key, "count": count}
        for day_key, count in date_to_counts.items()
    ]


def aggregate_statistics(memories: list[MemoryRecord]) -> MemoryStatistics:
    """Aggregate a list of memory records into a statistics payload.

    Args:
        memories: The memory record list (as returned by ``list_memory``).

    Returns:
        A :class:`MemoryStatistics` dict with total/today/this_week/
        this_month counts, category breakdown, tag breakdown, a 30-day
        daily count series, and the last-updated timestamp.
    """
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total = len(memories)
    today_count = 0
    week_count = 0
    month_count = 0
    last_updated_ts: datetime | None = None

    category_counter: Counter[str] = Counter()
    tag_counter: Counter[str] = Counter()

    for memory in memories:
        created = _parse_timestamp(memory.get("created_at"))
        updated = _parse_timestamp(memory.get("updated_at"))

        if created is not None:
            if created >= today_start:
                today_count += 1
            if created >= week_ago:
                week_count += 1
            if created >= month_ago:
                month_count += 1

        if updated is not None and (
            last_updated_ts is None or updated > last_updated_ts
        ):
            last_updated_ts = updated

        category_counter[_extract_category(memory)] += 1
        for tag in _extract_tags(memory):
            tag_counter[tag] += 1

    categories: list[CategoryStat] = [
        {"category": cat, "count": count}
        for cat, count in category_counter.most_common()
    ]
    tags: list[TagStat] = [
        {"tag": tag, "count": count}
        for tag, count in tag_counter.most_common()
    ]
    daily_counts = _build_daily_counts(memories, now)

    last_updated: str | None = None
    if last_updated_ts is not None:
        last_updated = last_updated_ts.isoformat()

    return {
        "total": total,
        "today": today_count,
        "this_week": week_count,
        "this_month": month_count,
        "categories": categories,
        "tags": tags,
        "daily_counts": daily_counts,
        "last_updated": last_updated,
    }


__all__ = ["aggregate_statistics", "DAILY_WINDOW_DAYS", "UNCATEGORIZED"]
