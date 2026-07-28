"""Binary sensor platform for CKW Dynamic Pricing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CKWPricingCoordinator
from .const import DOMAIN
from .price import get_current_price


@dataclass(frozen=True, kw_only=True)
class CKWBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe CKW binary sensors."""

    threshold_key: str
    comparator: Callable[[float, float], bool]


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
        threshold = self._threshold
        if current_price is None or threshold is None:
            return False
        return self.entity_description.comparator(current_price, threshold)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return threshold details."""
        return {
            "current_price": self._current_price,
            "threshold": self._threshold,
        }

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
        threshold = self.coordinator.data.get(self.entity_description.threshold_key)
        return float(threshold) if threshold is not None else None
