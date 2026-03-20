"""Sensor platform for CKW Dynamic Pricing."""
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, CKWPricingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        CKWCurrentPriceSensor(coordinator, entry),
        CKWMinPriceSensor(coordinator, entry),
        CKWMaxPriceSensor(coordinator, entry),
        CKWAvgPriceSensor(coordinator, entry),
    ]
    
    async_add_entities(sensors)


class CKWPriceSensorBase(SensorEntity):
    """Base class for CKW price sensors."""
    
    _attr_unit_of_measurement = "Rp/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    
    def __init__(self, coordinator: CKWPricingCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "CKW Dynamic Pricing",
            "manufacturer": "CKW",
        }
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data


class CKWCurrentPriceSensor(CKWPriceSensorBase):
    """Sensor for current price."""
    
    _attr_name = "CKW Current Price"
    _attr_unique_id = "ckw_current_price"
    _attr_icon = "mdi:flash"
    
    @property
    def state(self):
        """Return the state."""
        if self.coordinator.
            return round(self.coordinator.data.get("current_price", 0), 2)
        return None


class CKWMinPriceSensor(CKWPriceSensorBase):
    """Sensor for minimum daily price."""
    
    _attr_name = "CKW Today Min Price"
    _attr_unique_id = "ckw_today_min_price"
    _attr_icon = "mdi:trending-down"
    
    @property
    def state(self):
        """Return the state."""
        if self.coordinator.
            return round(self.coordinator.data.get("min_price", 0), 2)
        return None


class CKWMaxPriceSensor(CKWPriceSensorBase):
    """Sensor for maximum daily price."""
    
    _attr_name = "CKW Today Max Price"
    _attr_unique_id = "ckw_today_max_price"
    _attr_icon = "mdi:trending-up"
    
    @property
    def state(self):
        """Return the state."""
        if self.coordinator.
            return round(self.coordinator.data.get("max_price", 0), 2)
        return None


class CKWAvgPriceSensor(CKWPriceSensorBase):
    """Sensor for average daily price."""
    
    _attr_name = "CKW Today Avg Price"
    _attr_unique_id = "ckw_today_avg_price"
    _attr_icon = "mdi:chart-line"
    
    @property
    def state(self):
        """Return the state."""
        if self.coordinator.
            return round(self.coordinator.data.get("avg_price", 0), 2)
        return None
