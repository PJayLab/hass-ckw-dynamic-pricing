"""Sensor platform for CKW Dynamic Pricing."""
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
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

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CKWPricingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)

        self.entry = entry

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="CKW",
            model="Dynamic Pricing",
        )


class CKWCurrentPriceSensor(CKWPriceSensorBase):
    """Sensor for current CKW price."""

    def __init__(   
            self,
            coordinator: CKWPricingCoordinator,
            entry: ConfigEntry,
        ) -> None:
        super().__init__(coordinator, entry)

        self._attr_native_value = None
        self._remove_listener = None
        self._attr_unique_id = f"{entry.entry_id}_current_price"
        self._attr_name = "Current price"
        self._attr_native_unit_of_measurement = "CHF/kWh"
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_state_class = SensorStateClass.MEASUREMENT

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
        await self._update_current_price(None)

    async def async_will_remove_from_hass(self):
        """Cleanup."""

        if self._remove_listener:
            self._remove_listener()

        await super().async_will_remove_from_hass()

    async def _update_current_price(self, now):
        """Calculate current price from cached API data."""
        _LOGGER.debug("Current price update triggered at %s", dt_util.now())
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
                _LOGGER.warning(
                    "Invalid CKW price entry: %s",
                    err,
                )

        self._attr_native_value = (
            round(current_price, 4)
            if current_price is not None
            else None
        )

        self.async_write_ha_state()


class CKWMinPriceSensor(CKWPriceSensorBase):
    """Sensor for minimum CKW price."""

    def __init__(   
            self,
            coordinator: CKWPricingCoordinator,
            entry: ConfigEntry,
        ) -> None:
        super().__init__(coordinator, entry)

        self._attr_unique_id = f"{entry.entry_id}_min_price"
        self._attr_name = "Minimum price"
        self._attr_native_unit_of_measurement = "CHF/kWh"
        self._attr_icon = "mdi:arrow-down"

    @property
    def native_value(self):
        if self.coordinator.data:
            return None
        return self.coordinator.data.get("min_price")


class CKWMaxPriceSensor(CKWPriceSensorBase):
    """Sensor for maximum CKW price."""

    def __init__(   
            self,
            coordinator: CKWPricingCoordinator,
            entry: ConfigEntry,
        ) -> None:
        super().__init__(coordinator, entry)

        self._attr_unique_id = f"{entry.entry_id}_max_price"
        self._attr_name = "Maximum price"
        self._attr_native_unit_of_measurement = "CHF/kWh"
        self._attr_icon = "mdi:arrow-up"

    @property
    def native_value(self):
        if self.coordinator.data:
            return None
        return self.coordinator.data.get("max_price")


class CKWAvgPriceSensor(CKWPriceSensorBase):
    """Sensor for average CKW price."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)

        self._attr_unique_id = f"{entry.entry_id}_avg_price"
        self._attr_name = "Average price"
        self._attr_native_unit_of_measurement = "CHF/kWh"
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self):
        if self.coordinator.data:
            return None
        return self.coordinator.data.get("avg_price")


class CKWAllPricesSensor(CKWPriceSensorBase):
    """Sensor for all CKW prices."""

    def __init__(   
            self,
            coordinator: CKWPricingCoordinator,
            entry: ConfigEntry,
        ) -> None:
        super().__init__(coordinator, entry)

        self._attr_unique_id = f"{entry.entry_id}_all_prices"
        self._attr_name = "All prices"
        self._attr_native_unit_of_measurement = "Einträge"
        self._attr_icon = "mdi:format-list-bulleted"

    @property
    def native_value(self):
        if self.coordinator.data:
            return len(self.coordinator.data.get("prices", []))

        return None


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