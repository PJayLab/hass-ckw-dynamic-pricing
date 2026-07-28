"""Binary sensor platform for CKW Dynamic Pricing."""
import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import entity_registry as er

from . import CKWPricingCoordinator, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor platform."""
    coordinator: CKWPricingCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        CKWBelowThresholdBinarySensor(coordinator, entry),
    ]

    async_add_entities(entities)


class CKWBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for CKW binary sensors."""

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

class CKWBelowThresholdBinarySensor(CKWBinarySensorBase):
    """Binary sensor for CKW price below threshold."""

    def __init__(
        self,
        coordinator: CKWPricingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)

        self._attr_unique_id = f"{entry.entry_id}_below_threshold"
        self._attr_name = "Below threshold"
        self._attr_icon = "mdi:close-circle"

    @property
    def is_on(self) -> bool:
        """Return True if price is below threshold."""

        if not self.coordinator.data:
            return False

        state = self.hass.states.get("sensor.ckw_current_price")

        if state is None or state.state in ("unknown", "unavailable"):
            return False

        current_price = float(state.state)
        threshold = float(self.coordinator.data.get("threshold", 0.10))

        return current_price < threshold


    @property
    def extra_state_attributes(self) -> dict:
        state = self.hass.states.get("sensor.ckw_current_price")

        return {
            "current_price": state.state if state else None,
            "threshold": self.coordinator.data.get("threshold", 0.10),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
