from homeassistant import config_entries
import voluptuous as vol

from . import CONF_NAME, CONF_NETWORK, CONF_POOL_ADDRESS

class GeckoTerminalOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_NAME, default=self.config_entry.data.get(CONF_NAME)): str,
            vol.Required(CONF_NETWORK, default=self.config_entry.data.get(CONF_NETWORK)): str,
            vol.Required(CONF_POOL_ADDRESS, default=self.config_entry.data.get(CONF_POOL_ADDRESS)): str,
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)