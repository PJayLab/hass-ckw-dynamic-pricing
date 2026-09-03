"""Button platform for CKW Dynamic Pricing."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CKWPricingCoordinator
from .const import DOMAIN


REFRESH_TARIFFS_DESCRIPTION = ButtonEntityDescription(
    key="refresh_tariffs",
    translation_key="refresh_tariffs",
    icon="mdi:refresh",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the configuration button."""
    coordinator: CKWPricingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CKWRefreshTariffsButton(coordinator, entry)])


class CKWRefreshTariffsButton(CoordinatorEntity, ButtonEntity):
    """Button that immediately fetches the latest tariff schedules."""

    _attr_has_entity_name = True
    entity_description = REFRESH_TARIFFS_DESCRIPTION

    def __init__(self, coordinator: CKWPricingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the refresh button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{self.entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="CKW",
            model="Dynamic Pricing",
        )

    async def async_press(self) -> None:
        """Fetch tariff data now."""
        await self.coordinator.async_request_refresh()
