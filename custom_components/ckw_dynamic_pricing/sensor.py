"""Sensor platform for CKW Dynamic Pricing."""
import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CKWPricingCoordinator, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    coordinator: CKWPricingCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        CKWCurrentPriceSensor(coordinator, entry),
        CKWMinPriceSensor(coordinator, entry),
        CKWMaxPriceSensor(coordinator, entry),
        CKWAvgPriceSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class CKWPriceSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for CKW price sensors."""

    def __init__(self, coordinator: CKWPricingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class CKWCurrentPriceSensor(CKWPriceSensorBase):
    """Sensor for current CKW price."""

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{self.entry.entry_id}_current_price"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "CKW Current Price"

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("current_price", 0)
        return 0

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "Rp/kWh"

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:lightning-bolt"

    @property
    def state_class(self) -> SensorStateClass:
        """Return the state class."""
        return SensorStateClass.MEASUREMENT


class CKWMinPriceSensor(CKWPriceSensorBase):
    """Sensor for minimum CKW price."""

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{self.entry.entry_id}_min_price"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "CKW Min Price"

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("min_price", 0)
        return 0

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "Rp/kWh"

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:arrow-down"


class CKWMaxPriceSensor(CKWPriceSensorBase):
    """Sensor for maximum CKW price."""

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{self.entry.entry_id}_max_price"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "CKW Max Price"

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("max_price", 0)
        return 0

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "Rp/kWh"

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:arrow-up"


class CKWAvgPriceSensor(CKWPriceSensorBase):
    """Sensor for average CKW price."""

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{self.entry.entry_id}_avg_price"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "CKW Avg Price"

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("avg_price", 0)
        return 0

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "Rp/kWh"

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:chart-line"
