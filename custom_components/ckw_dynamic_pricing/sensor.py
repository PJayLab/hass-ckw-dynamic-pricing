"""Sensor platform for CKW Dynamic Pricing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CKWPricingCoordinator
from .const import DOMAIN
from .price import (
    get_all_prices,
    get_current_price,
    get_daily_statistics,
    get_extreme_window,
    get_next_change,
)


@dataclass(frozen=True, kw_only=True)
class CKWPriceSensorEntityDescription(SensorEntityDescription):
    """Describe CKW price sensors."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS = (
    CKWPriceSensorEntityDescription(
        key="current_price",
        translation_key="current_price",
        native_unit_of_measurement="CHF/kWh",
        icon="mdi:lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("current_price"),
    ),
    CKWPriceSensorEntityDescription(
        key="next_change",
        translation_key="next_change",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: get_next_change(data.get("prices", [])),
    ),
    CKWPriceSensorEntityDescription(
        key="average_price_today",
        translation_key="average_price_today",
        native_unit_of_measurement="CHF/kWh",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("avg_price"),
    ),
    CKWPriceSensorEntityDescription(
        key="average_price_tomorrow",
        translation_key="average_price_tomorrow",
        native_unit_of_measurement="CHF/kWh",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _average(data.get("prices_tomorrow", [])),
    ),
    *(
        CKWPriceSensorEntityDescription(
            key=f"{edge}_{hours}h_window_{day}",
            translation_key=f"{edge}_{hours}h_window_{day}",
            native_unit_of_measurement="CHF/kWh",
            icon="mdi:calendar-clock",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
            value_fn=lambda data, edge=edge, hours=hours, day=day: _window_value(
                data.get(f"prices_{day}", []), hours, edge
            ),
        )
        for day in ("today", "tomorrow")
        for edge in ("lowest", "highest")
        for hours in (2, 4)
    ),
    CKWPriceSensorEntityDescription(
        key="min_price",
        translation_key="min_price",
        native_unit_of_measurement="CHF/kWh",
        icon="mdi:arrow-down",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("min_price"),
    ),
    CKWPriceSensorEntityDescription(
        key="max_price",
        translation_key="max_price",
        native_unit_of_measurement="CHF/kWh",
        icon="mdi:arrow-up",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("max_price"),
    ),
    CKWPriceSensorEntityDescription(
        key="avg_price",
        translation_key="avg_price",
        native_unit_of_measurement="CHF/kWh",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("avg_price"),
    ),
    CKWPriceSensorEntityDescription(
        key="all_prices",
        translation_key="all_prices",
        icon="mdi:format-list-bulleted",
        value_fn=lambda data: len(data.get("prices", [])),
    ),
)


def _average(prices: list[dict[str, Any]]) -> float | None:
    """Get the daily average from a price list."""
    statistics = get_daily_statistics(prices)
    if not statistics:
        return None
    values = [item["price"] for item in get_all_prices(prices)]
    return round(sum(values) / len(values), 4) if values else None


def _window_value(prices: list[dict[str, Any]], hours: int, edge: str) -> float | None:
    """Get an extreme window's average price."""
    window = get_extreme_window(prices, hours, "min" if edge == "lowest" else "max")
    return window["average"] if window else None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up sensor platform."""
    coordinator: CKWPricingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(CKWPriceSensor(coordinator, entry, description) for description in SENSOR_DESCRIPTIONS)


class CKWPriceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for CKW price data."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CKWPricingCoordinator, entry: ConfigEntry, description: CKWPriceSensorEntityDescription) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._remove_listener = None
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.title, manufacturer="CKW", model="Dynamic Pricing")

    async def async_added_to_hass(self) -> None:
        """Register quarter-hour state refreshes for time-dependent prices."""
        await super().async_added_to_hass()
        self._remove_listener = async_track_time_change(
            self.hass,
            self._handle_time_change,
            minute=(0, 15, 30, 45),
            second=5,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove registered listeners."""
        if self._remove_listener:
            self._remove_listener()
        await super().async_will_remove_from_hass()

    async def _handle_time_change(self, now) -> None:
        """Refresh entity states when CKW price slots change."""
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the native sensor value."""
        if not self.coordinator.data:
            return None
        if self.entity_description.key == "current_price":
            return get_current_price(self.coordinator.data.get("prices", []))
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        key = self.entity_description.key
        if key == "all_prices":
            return {"prices": get_all_prices(self.coordinator.data.get("prices", []))}
        if key in ("average_price_today", "average_price_tomorrow"):
            day = key.rsplit("_", 1)[1]
            return {
                "day": day,
                **(get_daily_statistics(self.coordinator.data.get(f"prices_{day}", [])) or {}),
            }
        if "_window_" in key:
            edge, remainder = key.split("_", 1)
            hours = int(remainder.split("h_", 1)[0])
            day = remainder.rsplit("_", 1)[1]
            window = get_extreme_window(
                self.coordinator.data.get(f"prices_{day}", []),
                hours,
                "min" if edge == "lowest" else "max",
            )
            if not window:
                return {}
            return {
                "window_start": window["start"],
                "window_end": window["end"],
                "window_minutes": hours * 60,
                "mode": window["mode"],
                "day": day,
            }
        return {}
