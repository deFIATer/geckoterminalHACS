"""Config flow for GeckoTerminal integration."""
from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
import logging

from . import CONF_NAME, CONF_NETWORK, CONF_POOL_ADDRESS, DOMAIN
from . import CONF_SHOW_VOLUME, CONF_DECIMAL_PLACES, CONF_SHOW_FDV, CONF_UPDATE_INTERVAL
from . import DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Lista popularnych sieci jako przykłady
EXAMPLE_NETWORKS = [
    "ethereum", "bsc", "polygon", "arbitrum", "optimism", "avalanche",
    "fantom", "celo", "gnosis", "base", "zksync", "abstract"
]

class GeckoTerminalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GeckoTerminal."""
    
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Utworzenie unikalnego ID na podstawie sieci i adresu puli
            unique_id = f"{user_input[CONF_NETWORK]}_{user_input[CONF_POOL_ADDRESS]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            
            _LOGGER.debug(f"Konfiguracja GeckoTerminal: {user_input}")
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        # Domyślne wartości
        suggested_values = {
            CONF_NAME: "",
            CONF_NETWORK: "ethereum",
            CONF_POOL_ADDRESS: "",
            CONF_SHOW_VOLUME: True,
            CONF_DECIMAL_PLACES: 2,
            CONF_SHOW_FDV: True,
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL
        }
        
        # Jeśli użytkownik już wprowadził dane, zachowaj je
        if user_input is not None:
            suggested_values.update(user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_NAME, default=suggested_values[CONF_NAME]): str,
            vol.Required(CONF_NETWORK, default=suggested_values[CONF_NETWORK]): str,
            vol.Required(CONF_POOL_ADDRESS, default=suggested_values[CONF_POOL_ADDRESS]): str,
            vol.Optional(CONF_SHOW_VOLUME, default=suggested_values[CONF_SHOW_VOLUME]): bool,
            vol.Optional(CONF_DECIMAL_PLACES, default=suggested_values[CONF_DECIMAL_PLACES]): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=8)
            ),
            vol.Optional(CONF_SHOW_FDV, default=suggested_values[CONF_SHOW_FDV]): bool,
            vol.Optional(CONF_UPDATE_INTERVAL, default=suggested_values[CONF_UPDATE_INTERVAL]): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=60)
            ),
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
        """Get the options flow for this handler."""
        return GeckoTerminalOptionsFlow(config_entry)


class GeckoTerminalOptionsFlow(config_entries.OptionsFlow):
    """Handle options for GeckoTerminal."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Pobierz obecne ustawienia
        data = {**self.config_entry.data}
        
        # Dodaj brakujące opcje z domyślnymi wartościami, jeśli nie istnieją
        if CONF_SHOW_VOLUME not in data:
            data[CONF_SHOW_VOLUME] = True
        if CONF_DECIMAL_PLACES not in data:
            data[CONF_DECIMAL_PLACES] = 2
        if CONF_SHOW_FDV not in data:
            data[CONF_SHOW_FDV] = True
        if CONF_UPDATE_INTERVAL not in data:
            data[CONF_UPDATE_INTERVAL] = DEFAULT_UPDATE_INTERVAL

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=data.get(CONF_NAME),
                    ): str,
                    vol.Required(
                        CONF_NETWORK,
                        default=data.get(CONF_NETWORK),
                    ): str,
                    vol.Required(
                        CONF_POOL_ADDRESS,
                        default=data.get(CONF_POOL_ADDRESS),
                    ): str,
                    vol.Optional(
                        CONF_SHOW_VOLUME,
                        default=data.get(CONF_SHOW_VOLUME),
                    ): bool,
                    vol.Optional(
                        CONF_DECIMAL_PLACES,
                        default=data.get(CONF_DECIMAL_PLACES),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=8)),
                    vol.Optional(
                        CONF_SHOW_FDV,
                        default=data.get(CONF_SHOW_FDV),
                    ): bool,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=data.get(CONF_UPDATE_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                }
            ),
        )