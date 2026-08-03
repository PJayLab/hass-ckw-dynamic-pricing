"""Binary sensor platform for CKW Dynamic Pricing."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import CKWPricingCoordinator
from .const import DOMAIN
from .price import get_current_price, get_extreme_window, get_quantile_slots


@dataclass(frozen=True, kw_only=True)
class CKWBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe CKW binary sensors."""

    threshold_key: str | None = None
    comparator: Callable[[float, float], bool] | None = None
    quantile: float | None = None
    mode: str | None = None
    window_hours: int | None = None


BINARY_SENSOR_DESCRIPTIONS = (
    CKWBinarySensorEntityDescription(
        key="below_low_price_threshold",
        translation_key="below_low_price_threshold",
        icon="mdi:arrow-down-bold-circle",
        threshold_key="low_price_threshold",
        comparator=lambda current_price, threshold: current_price < threshold,
    ),
    CKWBinarySensorEntityDescription(
        key="above_high_price_threshold",
        translation_key="above_high_price_threshold",
        icon="mdi:arrow-up-bold-circle",
        threshold_key="high_price_threshold",
        comparator=lambda current_price, threshold: current_price > threshold,
    ),
)

BINARY_SENSOR_DESCRIPTIONS += tuple(
    CKWBinarySensorEntityDescription(
        key=f"{mode}_{percent}_percent_hours_today",
        translation_key=f"{mode}_{percent}_percent_hours_today",
        icon="mdi:percent",
        entity_registry_enabled_default=False,
        quantile=percent / 100,
        mode="cheap" if mode == "cheapest" else "expensive",
    )
    for mode in ("cheapest", "most_expensive")
    for percent in (10, 25, 50)
) + tuple(
    CKWBinarySensorEntityDescription(
        key=f"in_{edge}_{hours}h_window_today",
        translation_key=f"in_{edge}_{hours}h_window_today",
        icon="mdi:calendar-clock",
        entity_registry_enabled_default=False,
        mode="min" if edge == "lowest" else "max",
        window_hours=hours,
    )
    for edge in ("lowest", "highest")
    for hours in (2, 4)
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up binary sensor platform."""
    coordinator: CKWPricingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(CKWThresholdBinarySensor(coordinator, entry, description) for description in BINARY_SENSOR_DESCRIPTIONS)


class CKWThresholdBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for CKW price threshold checks."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CKWPricingCoordinator, entry: ConfigEntry, description: CKWBinarySensorEntityDescription) -> None:
        """Initialize the binary sensor."""
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
        """Refresh threshold states when CKW price slots change."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if the current price matches the threshold rule."""
        current_price = self._current_price
        if current_price is None:
            return False
        if self.entity_description.quantile is not None:
            qualifying = get_quantile_slots(
                self.coordinator.data.get("prices_today", []),
                self.entity_description.quantile,
                self.entity_description.mode or "cheap",
            )
            if not qualifying:
                return False
            _, slots = qualifying
            now = dt_util.now()
            return any(_slot_contains_now(slot, now) for slot in slots)
        if self.entity_description.window_hours is not None:
            window = get_extreme_window(
                self.coordinator.data.get("prices_today", []),
                self.entity_description.window_hours,
                self.entity_description.mode or "min",
            )
            now = dt_util.now()
            return bool(window and window["start"] <= now < window["end"])
        threshold = self._threshold
        return bool(
            threshold is not None
            and self.entity_description.comparator
            and self.entity_description.comparator(current_price, threshold)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return threshold details."""
        attributes = {
            "current_price": self._current_price,
            "threshold": self._threshold,
        }
        if self.entity_description.quantile is not None and self.coordinator.data:
            qualifying = get_quantile_slots(
                self.coordinator.data.get("prices_today", []),
                self.entity_description.quantile,
                self.entity_description.mode or "cheap",
            )
            if qualifying:
                threshold, slots = qualifying
                attributes.update(
                    {
                        "quantile": self.entity_description.quantile,
                        "mode": self.entity_description.mode,
                        "threshold_price": threshold,
                        "qualifying_slots": slots,
                    }
                )
        if self.entity_description.window_hours is not None and self.coordinator.data:
            window = get_extreme_window(
                self.coordinator.data.get("prices_today", []),
                self.entity_description.window_hours,
                self.entity_description.mode or "min",
            )
            if window:
                attributes.update(
                    {
                        "mode": window["mode"],
                        "window_start": window["start"],
                        "window_end": window["end"],
                        "window_average_price": window["average"],
                        "window_hours": window["hours"],
                    }
                )
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self._current_price is not None

    @property
    def _current_price(self) -> float | None:
        """Return the active price using the shared helper."""
        if not self.coordinator.data:
            return None
        return get_current_price(self.coordinator.data.get("prices", []))

    @property
    def _threshold(self) -> float | None:
        """Return the configured threshold for this entity."""
        if not self.coordinator.data:
            return None
        if not self.entity_description.threshold_key:
            return None
        threshold = self.coordinator.data.get(self.entity_description.threshold_key)
        return float(threshold) if threshold is not None else None


def _slot_contains_now(slot: dict[str, Any], now: datetime) -> bool:
    """Return whether a normalized price slot contains ``now``."""
    start = datetime.fromisoformat(slot["start"])
    end = datetime.fromisoformat(slot["end"])
    if start.tzinfo is None:
        start = start.replace(tzinfo=now.tzinfo)
    if end.tzinfo is None:
        end = end.replace(tzinfo=now.tzinfo)
    return start <= now < end
