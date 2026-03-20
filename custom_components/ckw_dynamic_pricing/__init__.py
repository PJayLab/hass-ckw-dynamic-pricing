"""CKW Dynamic Pricing Integration for Home Assistant."""
import logging
from datetime import timedelta
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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    params={"netzebene": self.config.get("netzebene", "N1")},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"CKW API returned {resp.status}")
                    
                    data = await resp.json()
                    return self._process_data(data)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error connecting to CKW API: {err}") from err

    def _process_data(self,data:Dict[str, Any]) -> Dict[str, Any]:
        """Process API data."""
        preisdaten = data.get("preisdaten", [])
        
        if not preisdaten:
            return {}

        prices = [p["preis_ct_pro_kwh"] for p in preisdaten]
        current_hour = 0
        
        return {
            "current_price": prices[current_hour] if current_hour < len(prices) else 0,
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": sum(prices) / len(prices) if prices else 0,
            "threshold": self.config.get("price_threshold", 10),
            "prices": preisdaten,
        }
