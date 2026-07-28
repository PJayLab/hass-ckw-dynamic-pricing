"""Price calculation helpers for CKW Dynamic Pricing."""

from __future__ import annotations

import logging
from datetime import datetime
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
