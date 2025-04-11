DOMAIN = "geckoterminal"

import logging
from homeassistant.helpers.discovery import async_load_platform

CONF_NAME = "name"
CONF_NETWORK = "network"
CONF_POOL_ADDRESS = "pool_address"

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, config_entry):
    _LOGGER.debug(f"Setting up GeckoTerminal integration with config: {config_entry.data}")
    
    try:
        hass.async_create_task(
            async_load_platform(
                hass, 
                "sensor", 
                DOMAIN, 
                config_entry.data, 
                config_entry.data
            )
        )
        _LOGGER.debug("GeckoTerminal sensor platform loaded successfully")
        return True
    except Exception as e:
        _LOGGER.error(f"Failed to set up GeckoTerminal integration: {e}")
        return False