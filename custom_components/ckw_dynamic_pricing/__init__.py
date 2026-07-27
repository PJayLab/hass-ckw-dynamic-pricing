"""CKW Dynamic Pricing Integration for Home Assistant."""
import logging
from datetime import datetime, timedelta, time
from typing import Any, Dict

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ckw_dynamic_pricing"
PLATFORMS = ["sensor", "binary_sensor"]
SCAN_INTERVAL = timedelta(hours=6)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CKW Dynamic Pricing from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = CKWPricingCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class CKWPricingCoordinator(DataUpdateCoordinator):
    """Coordinator for CKW pricing data."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.config = config
        self.api_url = "https://e-ckw-public-data.de-c1.eu1.cloudhub.io/api/v1/netzinformationen/energie/dynamische-preise"

    async def _fetch_day(self, session: aiohttp.ClientSession, date) -> list:
        """Fetch prices for a specific date."""
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)

        start = datetime.combine(
            date,
            time.min,
            tzinfo=local_tz,
        ).isoformat()

        end = datetime.combine(
            date,
            time.max,
            tzinfo=local_tz,
        ).isoformat()
        params = {
            "tariff_name": self.config.get("tariff_name", "home_dynamic"),
            "start_timestamp": start,
            "end_timestamp": end,
            "tariff_type": "integrated",
        }
        try:
            async with session.get(
                self.api_url,
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

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from CKW API for today and tomorrow."""
        threshold_state = self.hass.states.get("input_number.ckw_price_threshold")
        threshold = float(threshold_state.state) if threshold_state else self.config.get("price_threshold", 10)

        today = dt_util.now().date()
        tomorrow = today + timedelta(days=1)

        try:
            async with aiohttp.ClientSession() as session:
                prices_today = await self._fetch_day(session, today)
                prices_tomorrow = await self._fetch_day(session, tomorrow)

            if not prices_today:
                raise UpdateFailed("No price data received from CKW API for today")

            combined = prices_today + prices_tomorrow
            return self._process_data(prices_today, combined, threshold)

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error connecting to CKW API: {err}") from err

    def _process_data(
        self,
        prices_today: list,
        prices_all: list,
        threshold: float = 10,
    ) -> Dict[str, Any]:
        """Process API data."""

        if not prices_today:
            return {}

        today_prices = [
            entry["integrated"][0]["value"]
            for entry in prices_today
            if "integrated" in entry and entry["integrated"]
        ]

        if not today_prices:
            raise UpdateFailed("No price data found in API response")

        return {
            "min_price": round(min(today_prices), 4),
            "max_price": round(max(today_prices), 4),
            "avg_price": round(sum(today_prices) / len(today_prices), 4),
            "threshold": threshold,
            "prices": prices_all,
        }
