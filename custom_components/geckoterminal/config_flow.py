from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from . import CONF_NAME, CONF_NETWORK, CONF_POOL_ADDRESS, DOMAIN
from .options_flow import GeckoTerminalOptionsFlowHandler

class GeckoTerminalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_NETWORK]}_{user_input[CONF_POOL_ADDRESS]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_NETWORK): str,
            vol.Required(CONF_POOL_ADDRESS): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GeckoTerminalOptionsFlowHandler(config_entry)