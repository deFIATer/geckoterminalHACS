import requests
from homeassistant.const import CURRENCY_USD
from homeassistant.helpers.entity import Entity
import logging
from datetime import datetime, timedelta
import voluptuous as vol
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import CONF_NAME, CONF_NETWORK, CONF_POOL_ADDRESS

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return

    name = discovery_info[CONF_NAME]
    network = discovery_info[CONF_NETWORK]
    pool_address = discovery_info[CONF_POOL_ADDRESS]

    _LOGGER.debug(f"Setting up GeckoTerminal sensor with name: {name}, network: {network}, pool_address: {pool_address}")
    
    # Tworzymy koordynatora aktualizacji dla sensora
    coordinator = GeckoTerminalDataUpdateCoordinator(
        hass,
        name=name,
        network=network,
        pool_address=pool_address,
    )
    
    # Pierwsza aktualizacja danych
    await hass.async_add_executor_job(coordinator.async_refresh)
    
    async_add_entities([GeckoTerminalSensor(coordinator, name, network, pool_address)])

def validate_pool_address(network, pool_address):
    """Validate if the pool address exists for the given network."""
    url = f"https://api.geckoterminal.com/api/v2/networks/{network}/pools/{pool_address}"
    _LOGGER.debug(f"Walidacja puli: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        _LOGGER.debug(f"Status odpowiedzi: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Sprawdź pełną strukturę odpowiedzi
            if "data" in data:
                if "attributes" in data["data"]:
                    attributes = data["data"]["attributes"]
                    
                    # Zapisz wszystkie dostępne atrybuty do logów dla celów diagnostycznych
                    available_attrs = list(attributes.keys())
                    _LOGGER.debug(f"Dostępne atrybuty: {available_attrs}")
                    
                    if "base_token_price_usd" in attributes:
                        return True, None
                    else:
                        return False, f"Brak atrybutu 'base_token_price_usd' w odpowiedzi API. Dostępne: {available_attrs}"
                else:
                    return False, "Brak atrybutów w odpowiedzi API"
            else:
                return False, "Nieprawidłowa struktura danych z API - brak klucza 'data'"
        elif response.status_code == 404:
            return False, f"Sieć '{network}' lub adres puli '{pool_address}' nie zostały znalezione (404)"
        else:
            return False, f"API zwróciło kod statusu {response.status_code}"
    except Exception as e:
        return False, f"Błąd: {str(e)}"

class GeckoTerminalDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass, name, network, pool_address):
        """Initialize."""
        self.name = name
        self.network = network
        self.pool_address = pool_address
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"GeckoTerminal {name}",
            update_interval=timedelta(minutes=5),
        )

    def _fetch_data(self):
        """Fetch data from API endpoint."""
        url = f"https://api.geckoterminal.com/api/v2/networks/{self.network}/pools/{self.pool_address}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "data" in data and "attributes" in data["data"]:
                attributes = data["data"]["attributes"]
                result = {}
                
                # Pobierz wszystkie interesujące nas atrybuty
                attr_mapping = {
                    "base_token_price_usd": "state",
                    "base_token_symbol": "base_token_symbol",
                    "quote_token_symbol": "quote_token_symbol",
                    "total_liquidity_usd": "total_liquidity_usd",
                    "volume_usd": "volume_usd",
                    "fdv_usd": "fdv_usd",
                    "market_cap_usd": "market_cap_usd",
                    "price_change_percentage": "price_change_percentage",
                    "transactions": "transactions_24h",
                    "address": "pool_address",
                    "name": "pool_name"
                }
                
                for api_key, result_key in attr_mapping.items():
                    if api_key in attributes:
                        result[result_key] = attributes[api_key]
                
                # Dodaj czas ostatniej aktualizacji
                result["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                return result
            else:
                _LOGGER.error("Nieprawidłowa struktura danych z API")
                return None
        except Exception as e:
            _LOGGER.error(f"Błąd pobierania danych: {e}")
            return None

    async def _async_update_data(self):
        """Update data via executor."""
        return await self.hass.async_add_executor_job(self._fetch_data)

class GeckoTerminalSensor(CoordinatorEntity, SensorEntity):
    """Representation of a GeckoTerminal sensor."""

    def __init__(self, coordinator, name, network, pool_address):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._network = network
        self._pool_address = pool_address
        self._attr_unique_id = f"{network}_{pool_address}"
        self._unit_of_measurement = CURRENCY_USD
        self._attr_device_class = SensorDeviceClass.MONETARY
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.coordinator.data and "state" in self.coordinator.data:
            return self.coordinator.data["state"]
        return None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.coordinator.data:
            # Usuń klucz state z atrybutów, ponieważ to jest już stan sensora
            attrs = dict(self.coordinator.data)
            if "state" in attrs:
                del attrs["state"]
            return attrs
        return {}

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self._attr_unique_id

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:currency-usd"

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.data is not None