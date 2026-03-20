"""Config flow for CKW Dynamic Pricing integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ckw_dynamic_pricing"

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("price_threshold", default=10): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
    vol.Required("netzebene", default="N1"): vol.In(["N1", "N2", "N3"]),
})


class CKWConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CKW Dynamic Pricing."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="CKW Dynamic Pricing",
                    data=user_input,
                )
            except Exception as err:
                _LOGGER.error("Unexpected error: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
