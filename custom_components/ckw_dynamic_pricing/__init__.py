"""CKW Dynamic Pricing Integration for Home Assistant."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ckw_dynamic_pricing"
PLATFORMS = ["sensor", "binary_sensor"]
SCAN_INTERVAL = timedelta(hours=1)


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

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from CKW API."""
        threshold_state = self.hass.states.get("input_number.ckw_price_threshold")
        threshold = float(threshold_state.state) if threshold_state else self.config.get("price_threshold", 10)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"CKW API returned {resp.status}")
                    data = await resp.json()
                    return self._process_data(data, threshold)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error connecting to CKW API: {err}") from err

    def _process_data(self, data: Dict[str, Any], threshold: float = 10) -> Dict[str, Any]:
        """Process API data."""
        prices_raw = data.get("prices", [])
        if not prices_raw:
            return {}

        now = datetime.now(tz=timezone.utc)
                        
        current_price = 0.0
        for entry in prices_raw:
            try:
                start = datetime.fromisoformat(entry["start_timestamp"])
                end = datetime.fromisoformat(entry["end_timestamp"])

                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)

                if start <= now < end:
                    current_price = entry["integrated"][0]["value"]
                    break
            except (KeyError, IndexError, ValueError):
                continue

        all_prices = [
            entry["integrated"][0]["value"]
            for entry in prices_raw
            if "integrated" in entry and entry["integrated"]
        ]

        if not all_prices:
            raise UpdateFailed("No price data found in API response")
        
        return {
            "current_price": round(current_price * 100, 4),
            "min_price": round(min(all_prices) * 100, 4),
            "max_price": round(max(all_prices) * 100, 4),
            "avg_price": round(sum(all_prices) / len(all_prices) * 100, 4),
            "threshold": threshold,
            "prices": prices_raw,
        }
