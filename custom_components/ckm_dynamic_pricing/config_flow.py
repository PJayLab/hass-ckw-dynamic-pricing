"""Config flow for CKW Dynamic Pricing integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("price_threshold", default=10): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
    vol.Required("netzebene", default="N1"): vol.In(["N1", "N2", "N3"]),
})


class CKWConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CKW Dynamic Pricing."""
    
    VERSION = 1
    
    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id("ckw_dynamic_pricing")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="CKW Dynamic Pricing", data=user_input)
        
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            description_placeholders={
                "price_threshold": "Schwellenwert in Rappen pro kWh (z.B. 10)",
                "netzebene": "Netzebene der CKW (N1, N2 oder N3)",
            },
        )
