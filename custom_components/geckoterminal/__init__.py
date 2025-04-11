"""GeckoTerminal integration for Home Assistant."""

DOMAIN = "geckoterminal"

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.const import Platform

CONF_NAME = "name"
CONF_NETWORK = "network"
CONF_POOL_ADDRESS = "pool_address"
CONF_SHOW_VOLUME = "show_volume"
CONF_DECIMAL_PLACES = "decimal_places"
CONF_SHOW_FDV = "show_fdv"
CONF_UPDATE_INTERVAL = "update_interval"

# Domyślne wartości
DEFAULT_UPDATE_INTERVAL = 30  # sekundy

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config):
    """Set up the GeckoTerminal component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up GeckoTerminal from a config entry."""
    _LOGGER.debug(f"Setting up GeckoTerminal entry: {entry.data}")
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Utwórz obsługę opcji
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok