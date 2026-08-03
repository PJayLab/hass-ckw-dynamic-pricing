"""Price calculation helpers for CKW Dynamic Pricing."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from math import ceil
from typing import Any

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


def _parse_timestamp(
    timestamp: str,
) -> datetime | None:
    """Convert ISO timestamp to datetime."""

    try:
        dt = datetime.fromisoformat(timestamp)

        # CKW API may return timestamps without timezone
        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=dt_util.get_time_zone("Europe/Zurich")
            )

        return dt

    except ValueError:
        _LOGGER.warning(
            "Invalid timestamp: %s",
            timestamp,
        )
        return None


def get_current_price(
    prices: list[dict[str, Any]],
    now: datetime | None = None,
) -> float | None:
    """Return current active price."""

    if now is None:
        now = dt_util.now()

    for entry in prices:
        try:
            start = _parse_timestamp(
                entry["start_timestamp"]
            )
            end = _parse_timestamp(
                entry["end_timestamp"]
            )

            if start is None or end is None:
                continue

            if start <= now < end:
                return round(
                    float(
                        entry["integrated"][0]["value"]
                    ),
                    4,
                )

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as err:
            _LOGGER.warning(
                "Invalid CKW price entry: %s",
                err,
            )

    return None


def get_all_prices(
    prices: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return normalized price list."""

    result = []

    for entry in prices:
        try:
            result.append(
                {
                    "start": entry["start_timestamp"],
                    "end": entry["end_timestamp"],
                    "price": round(
                        float(
                            entry["integrated"][0]["value"]
                        ),
                        4,
                    ),
                }
            )

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ):
            continue

    return result


def get_next_change(prices: list[dict[str, Any]], now: datetime | None = None) -> datetime | None:
    """Return the end of the active price slot."""
    if now is None:
        now = dt_util.now()
    for entry in prices:
        start = _parse_timestamp(entry.get("start_timestamp", ""))
        end = _parse_timestamp(entry.get("end_timestamp", ""))
        if start and end and start <= now < end:
            return end
    return None


def get_daily_statistics(prices: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return statistics and coverage metadata for one day's price slots."""
    values = _get_values(prices)
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    durations = []
    for entry in prices:
        start = _parse_timestamp(entry.get("start_timestamp", ""))
        end = _parse_timestamp(entry.get("end_timestamp", ""))
        if start and end:
            durations.append((end - start).total_seconds() / 60)
    return {
        "min_price_chf_per_kwh": round(min(values), 4),
        "max_price_chf_per_kwh": round(max(values), 4),
        "median_price_chf_per_kwh": round(median, 4),
        "q25_price_chf_per_kwh": round(_percentile(ordered, 0.25), 4),
        "q75_price_chf_per_kwh": round(_percentile(ordered, 0.75), 4),
        "slots_count": len(values),
        "covered_minutes": round(sum(durations)),
    }


def get_extreme_window(
    prices: list[dict[str, Any]], hours: int, mode: str
) -> dict[str, Any] | None:
    """Find the cheapest or most expensive contiguous time window."""
    slots = []
    for entry in prices:
        start = _parse_timestamp(entry.get("start_timestamp", ""))
        end = _parse_timestamp(entry.get("end_timestamp", ""))
        values = _get_values([entry])
        if start and end and values:
            slots.append((start, end, values[0]))
    slots.sort(key=lambda slot: slot[0])
    target = timedelta(hours=hours)
    candidates = []
    for index, (start, _, _) in enumerate(slots):
        total = timedelta()
        values = []
        previous_end = start
        for slot_start, slot_end, value in slots[index:]:
            if slot_start != previous_end:
                break
            total += slot_end - slot_start
            values.append(value)
            previous_end = slot_end
            if total == target:
                candidates.append((sum(values) / len(values), start, slot_end))
                break
            if total > target:
                break
    if not candidates:
        return None
    average, start, end = (min if mode == "min" else max)(candidates, key=lambda item: item[0])
    return {"average": round(average, 4), "start": start, "end": end, "hours": hours, "mode": mode}


def get_quantile_slots(
    prices: list[dict[str, Any]], quantile: float, mode: str
) -> tuple[float, list[dict[str, Any]]] | None:
    """Return the threshold and slots in the cheapest/most-expensive quantile."""
    normalized = get_all_prices(prices)
    if not normalized:
        return None
    reverse = mode == "expensive"
    ranked = sorted(normalized, key=lambda slot: slot["price"], reverse=reverse)
    threshold = ranked[ceil(len(ranked) * quantile) - 1]["price"]
    qualifying = [slot for slot in normalized if slot["price"] >= threshold] if reverse else [slot for slot in normalized if slot["price"] <= threshold]
    return threshold, qualifying


def _percentile(values: list[float], fraction: float) -> float:
    """Calculate a linearly interpolated percentile from sorted values."""
    position = (len(values) - 1) * fraction
    lower, upper = int(position), ceil(position)
    return values[lower] if lower == upper else values[lower] + (values[upper] - values[lower]) * (position - lower)


def get_min_price(
    prices: list[dict[str, Any]],
) -> float | None:
    """Return minimum price."""

    values = _get_values(prices)

    return round(min(values), 4) if values else None


def get_max_price(
    prices: list[dict[str, Any]],
) -> float | None:
    """Return maximum price."""

    values = _get_values(prices)

    return round(max(values), 4) if values else None


def get_average_price(
    prices: list[dict[str, Any]],
) -> float | None:
    """Return average price."""

    values = _get_values(prices)

    if not values:
        return None

    return round(
        sum(values) / len(values),
        4,
    )


def _get_values(
    prices: list[dict[str, Any]],
) -> list[float]:
    """Extract price values."""

    values = []

    for entry in prices:
        try:
            values.append(
                float(
                    entry["integrated"][0]["value"]
                )
            )

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ):
            continue

    return values
