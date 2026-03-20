"""Binary sensor platform for CKW Dynamic Pricing."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, CKWPricingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        CKWBelowThresholdSensor(coordinator, entry),
    ]
    
    async_add_entities(sensors)


class CKWBelowThresholdSensor(BinarySensorEntity):
    """Binary sensor for price threshold check."""
    
    _attr_name = "CKW Below Threshold"
    _attr_unique_id = "ckw_below_threshold"
    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_icon = "mdi:flash-alert"
    
    def __init__(self, coordinator: CKWPricingCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "CKW Dynamic Pricing",
            "manufacturer": "CKW",
        }
    
    @property
    def is_on(self) -> bool:
        """Return true if price is below threshold."""
        if self.coordinator.
            return self.coordinator.data.get("below_threshold", False)
        return False
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data
