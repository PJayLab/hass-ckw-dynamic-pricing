"""Sensor platform for CKW Dynamic Pricing."""
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

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
        CKWAllPricesSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class CKWPriceSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for CKW price sensors."""

    def __init__(
        self,
        coordinator: CKWPricingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.entry = entry

    @property
    def available(self) -> bool:
        """Return availability."""
        return self.coordinator.last_update_success


class CKWCurrentPriceSensor(CKWPriceSensorBase):
    """Sensor for current CKW price."""

    def __init__(
        self,
        coordinator: CKWPricingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)

        self._attr_native_value = None
        self._remove_listener = None

    async def async_added_to_hass(self):
        """Register quarter-hour updates."""

        await super().async_added_to_hass()

        self._remove_listener = async_track_time_change(
            self.hass,
            self._update_current_price,
            minute=(0, 15, 30, 45),
            second=5,
        )

        # Initial update
        self._update_current_price(None)

    async def async_will_remove_from_hass(self):
        """Cleanup."""

        if self._remove_listener:
            self._remove_listener()

        await super().async_will_remove_from_hass()

    def _update_current_price(self, now):
        """Calculate current price from cached API data."""

        if not self.coordinator.data:
            self._attr_native_value = None
            self.async_write_ha_state()
            return

        prices = self.coordinator.data.get("prices", [])

        current_price = None
        now = dt_util.now()

        local_tz = dt_util.get_time_zone(
            self.hass.config.time_zone
        )

        for entry in prices:
            try:
                start = datetime.fromisoformat(
                    entry["start_timestamp"]
                )

                end = datetime.fromisoformat(
                    entry["end_timestamp"]
                )

                # Handle timestamps without timezone
                if start.tzinfo is None:
                    start = start.replace(tzinfo=local_tz)

                if end.tzinfo is None:
                    end = end.replace(tzinfo=local_tz)

                if start <= now < end:
                    current_price = entry["integrated"][0]["value"]
                    break

            except (KeyError, IndexError, ValueError) as err:
                _LOGGER.debug(
                    "Invalid CKW price entry: %s",
                    err,
                )

        self._attr_native_value = (
            round(current_price, 4)
            if current_price is not None
            else None
        )

        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        return f"{self.entry.entry_id}_current_price"

    @property
    def name(self) -> str:
        return "CKW Current Price"

    @property
    def native_unit_of_measurement(self) -> str:
        return "CHF/kWh"

    @property
    def icon(self) -> str:
        return "mdi:lightning-bolt"

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT


class CKWMinPriceSensor(CKWPriceSensorBase):
    """Sensor for minimum CKW price."""

    @property
    def unique_id(self):
        return f"{self.entry.entry_id}_min_price"

    @property
    def name(self):
        return "CKW Min Price"

    @property
    def native_value(self):
        if self.coordinator.data:
            return self.coordinator.data.get("min_price", 0)

        return 0

    @property
    def native_unit_of_measurement(self):
        return "CHF/kWh"

    @property
    def icon(self):
        return "mdi:arrow-down"


class CKWMaxPriceSensor(CKWPriceSensorBase):
    """Sensor for maximum CKW price."""

    @property
    def unique_id(self):
        return f"{self.entry.entry_id}_max_price"

    @property
    def name(self):
        return "CKW Max Price"

    @property
    def native_value(self):
        if self.coordinator.data:
            return self.coordinator.data.get("max_price", 0)

        return 0

    @property
    def native_unit_of_measurement(self):
        return "CHF/kWh"

    @property
    def icon(self):
        return "mdi:arrow-up"


class CKWAvgPriceSensor(CKWPriceSensorBase):
    """Sensor for average CKW price."""

    @property
    def unique_id(self):
        return f"{self.entry.entry_id}_avg_price"

    @property
    def name(self):
        return "CKW Avg Price"

    @property
    def native_value(self):
        if self.coordinator.data:
            return self.coordinator.data.get("avg_price", 0)

        return 0

    @property
    def native_unit_of_measurement(self):
        return "CHF/kWh"

    @property
    def icon(self):
        return "mdi:chart-line"


class CKWAllPricesSensor(CKWPriceSensorBase):
    """Sensor for all CKW prices."""

    @property
    def unique_id(self):
        return f"{self.entry.entry_id}_all_prices"

    @property
    def name(self):
        return "CKW All Prices"

    @property
    def native_value(self):
        if self.coordinator.data:
            return len(self.coordinator.data.get("prices", []))

        return 0

    @property
    def native_unit_of_measurement(self):
        return "Einträge"

    @property
    def icon(self):
        return "mdi:format-list-bulleted"

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}

        formatted = []

        for entry in self.coordinator.data.get("prices", []):
            try:
                formatted.append(
                    {
                        "start": entry["start_timestamp"],
                        "end": entry["end_timestamp"],
                        "price": round(
                            entry["integrated"][0]["value"],
                            4,
                        ),
                    }
                )

            except (KeyError, IndexError):
                continue

        return {
            "prices": formatted
        }