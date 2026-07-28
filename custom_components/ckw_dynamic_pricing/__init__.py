"""CKW Dynamic Pricing Integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_API_URL,
    CONF_HIGH_PRICE_THRESHOLD,
    CONF_LOW_PRICE_THRESHOLD,
    CONF_TARIFF_NAME,
    CONF_TARIFF_TYPE,
    DEFAULT_API_URL,
    DEFAULT_HIGH_PRICE_THRESHOLD,
    DEFAULT_LOW_PRICE_THRESHOLD,
    DEFAULT_TARIFF_NAME,
    DEFAULT_TARIFF_TYPE,
    DOMAIN,
    LEGACY_CONF_PRICE_THRESHOLD,
    PLATFORMS,
    SCAN_INTERVAL,
)
from .price import get_average_price, get_current_price, get_max_price, get_min_price

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CKW Dynamic Pricing from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = CKWPricingCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class CKWPricingCoordinator(DataUpdateCoordinator):
    """Coordinator for CKW pricing data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry

    @property
    def config(self) -> dict[str, Any]:
        """Return merged entry data and options."""
        return {**self.entry.data, **self.entry.options}

    async def _fetch_day(self, session: aiohttp.ClientSession, date) -> list:
        """Fetch prices for a specific date."""
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        start = datetime.combine(date, time.min, tzinfo=local_tz).isoformat()
        end = datetime.combine(date, time.max, tzinfo=local_tz).isoformat()
        params = {
            CONF_TARIFF_NAME: self.config.get(CONF_TARIFF_NAME, DEFAULT_TARIFF_NAME),
            "start_timestamp": start,
            "end_timestamp": end,
            CONF_TARIFF_TYPE: self.config.get(CONF_TARIFF_TYPE, DEFAULT_TARIFF_TYPE),
        }
        try:
            async with session.get(
                self.config.get(CONF_API_URL, DEFAULT_API_URL),
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("CKW API returned %s for date %s", resp.status, date)
                    return []
                data = await resp.json()
                return data.get("prices", [])
        except aiohttp.ClientError as err:
            _LOGGER.warning("Error fetching CKW data for date %s: %s", date, err)
            return []

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from CKW API for today and tomorrow."""
        today = dt_util.now().date()
        tomorrow = today + timedelta(days=1)

        try:
            async with aiohttp.ClientSession() as session:
                prices_today = await self._fetch_day(session, today)
                prices_tomorrow = await self._fetch_day(session, tomorrow)

            if not prices_today:
                raise UpdateFailed("No price data received from CKW API for today")

            combined = prices_today + prices_tomorrow
            return self._process_data(prices_today, combined)

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error connecting to CKW API: {err}") from err

    def _process_data(self, prices_today: list, prices_all: list) -> dict[str, Any]:
        """Process API data."""
        min_price = get_min_price(prices_today)
        max_price = get_max_price(prices_today)
        avg_price = get_average_price(prices_today)

        if min_price is None or max_price is None or avg_price is None:
            raise UpdateFailed("No price data found in API response")

        low_threshold = self.config.get(
            CONF_LOW_PRICE_THRESHOLD,
            self.config.get(LEGACY_CONF_PRICE_THRESHOLD, DEFAULT_LOW_PRICE_THRESHOLD),
        )
        high_threshold = self.config.get(
            CONF_HIGH_PRICE_THRESHOLD,
            DEFAULT_HIGH_PRICE_THRESHOLD,
        )

        return {
            "current_price": get_current_price(prices_all),
            "min_price": min_price,
            "max_price": max_price,
            "avg_price": avg_price,
            "low_price_threshold": float(low_threshold),
            "high_price_threshold": float(high_threshold),
            "prices": prices_all,
        }
