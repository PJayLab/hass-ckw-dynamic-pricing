"""Config flow for CKW Dynamic Pricing integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_HIGH_PRICE_THRESHOLD,
    CONF_LOW_PRICE_THRESHOLD,
    CONF_TARIFF_NAME,
    DEFAULT_HIGH_PRICE_THRESHOLD,
    DEFAULT_LOW_PRICE_THRESHOLD,
    DEFAULT_TARIFF_NAMES,
    DOMAIN,
    LEGACY_CONF_PRICE_THRESHOLD,
)

_LOGGER = logging.getLogger(__name__)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the shared configuration schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_TARIFF_NAME,
                default=defaults.get(CONF_TARIFF_NAME, DEFAULT_TARIFF_NAMES[0]),
            ): vol.In(DEFAULT_TARIFF_NAMES),
            vol.Required(
                CONF_LOW_PRICE_THRESHOLD,
                default=defaults.get(
                    CONF_LOW_PRICE_THRESHOLD,
                    defaults.get(LEGACY_CONF_PRICE_THRESHOLD, DEFAULT_LOW_PRICE_THRESHOLD),
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Required(
                CONF_HIGH_PRICE_THRESHOLD,
                default=defaults.get(
                    CONF_HIGH_PRICE_THRESHOLD,
                    DEFAULT_HIGH_PRICE_THRESHOLD,
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
        }
    )


class CKWConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CKW Dynamic Pricing."""

    VERSION = 1

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return CKWOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="CKW Dynamic Pricing",
                    data=user_input,
                )
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Unexpected error: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=_schema({}),
            errors=errors,
        )


class CKWOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for CKW Dynamic Pricing."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(defaults),
        )
