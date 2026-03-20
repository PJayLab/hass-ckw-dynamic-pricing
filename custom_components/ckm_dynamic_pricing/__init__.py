"""CKW Dynamic Pricing Integration for Home Assistant."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ckw_dynamic_pricing"
PLATFORMS = ["sensor", "binary_sensor"]

API_ENDPOINT = "https://e-ckw-public-data.de-c1.eu1.cloudhub.io/api/v1/netzinformationen/energie/dynamische-preise"
SCAN_INTERVAL = timedelta(hours=1)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CKW Dynamic Pricing from a config entry."""
    
    coordinator = CKWPricingCoordinator(hass, entry.data)
    
    # Initial fetch
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class CKWPricingCoordinator(DataUpdateCoordinator):
    """Coordinator for CKW Dynamic Pricing data."""
    
    def __init__(self, hass: HomeAssistant, config: dict):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.config = config
        self.price_threshold = config.get("price_threshold", 10)
        self.netzebene = config.get("netzebene", "N1")
        
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        API_ENDPOINT,
                        params={"stichtag": datetime.now().strftime("%Y-%m-%d")}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._process_data(data)
                        else:
                            raise UpdateFailed(f"API returned status {response.status}")
        except asyncio.TimeoutError as err:
            raise UpdateFailed("API timeout") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
    
    def _process_data(self, api_ dict) -> dict[str, Any]:
        """Process API data and calculate values."""
        try:
            preisdaten = api_data.get("preisdaten", [])
            
            if not preisdaten:
                _LOGGER.warning("No price data available")
                return {}
            
            # Get current hour price
            now = datetime.now()
            current_hour = now.hour
            
            current_price = None
            for preis in preisdaten:
                if preis.get("stunde") == current_hour:
                    current_price = preis.get("preis_ct_pro_kwh", 0)
                    break
            
            if current_price is None and preisdaten:
                current_price = preisdaten[0].get("preis_ct_pro_kwh", 0)
            
            # Calculate statistics
            prices = [p.get("preis_ct_pro_kwh", 0) for p in preisdaten]
            
            return {
                "current_price": current_price,
                "min_price": min(prices) if prices else 0,
                "max_price": max(prices) if prices else 0,
                "avg_price": sum(prices) / len(prices) if prices else 0,
                "below_threshold": current_price < self.price_threshold if current_price else False,
                "all_prices": prices,
                "updated_at": datetime.now().isoformat(),
            }
        except Exception as err:
            _LOGGER.error(f"Error processing  {err}")
            return {}
