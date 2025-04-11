from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
import logging

from . import CONF_NAME, CONF_NETWORK, CONF_POOL_ADDRESS, DOMAIN
from .options_flow import GeckoTerminalOptionsFlowHandler
from .sensor import validate_pool_address

_LOGGER = logging.getLogger(__name__)

# Lista popularnych sieci jako przykłady
EXAMPLE_NETWORKS = [
    "ethereum", "bsc", "polygon", "arbitrum", "optimism", "avalanche",
    "fantom", "celo", "gnosis", "base", "zksync", "abstract"
]

class GeckoTerminalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Sprawdzenie poprawności adresu puli dla podanej sieci
            valid, error_msg = validate_pool_address(user_input[CONF_NETWORK], user_input[CONF_POOL_ADDRESS])
            if not valid:
                errors[CONF_POOL_ADDRESS] = "invalid_pool_address"
                _LOGGER.error(f"Niepoprawny adres puli: {error_msg}")
            else:
                # Tworzymy unikalny identyfikator na podstawie sieci i adresu puli
                unique_id = f"{user_input[CONF_NETWORK]}_{user_input[CONF_POOL_ADDRESS]}"
                await self.async_set_unique_id(unique_id)
                # Jeśli już istnieje taki sensor, zwracamy AbortFlow
                self._abort_if_unique_id_configured()
                
                _LOGGER.debug(f"Konfiguracja GeckoTerminal: {user_input}")
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        # Domyślne wartości
        suggested_values = {
            CONF_NAME: "",
            CONF_NETWORK: "ethereum",
            CONF_POOL_ADDRESS: ""
        }
        
        # Jeśli użytkownik już wprowadził dane, zachowaj je
        if user_input is not None:
            suggested_values.update(user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_NAME, default=suggested_values[CONF_NAME]): str,
            vol.Required(CONF_NETWORK, default=suggested_values[CONF_NETWORK]): str,
            vol.Required(CONF_POOL_ADDRESS, default=suggested_values[CONF_POOL_ADDRESS]): str,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={"examples": ", ".join(EXAMPLE_NETWORKS[:5])}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GeckoTerminalOptionsFlowHandler(config_entry)