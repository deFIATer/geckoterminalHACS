"""GeckoTerminal sensor platform."""
import requests
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
import logging
import async_timeout
from datetime import datetime, timedelta

from . import DOMAIN, CONF_NAME, CONF_NETWORK, CONF_POOL_ADDRESS
from . import CONF_SHOW_VOLUME, CONF_DECIMAL_PLACES, CONF_SHOW_FDV, CONF_UPDATE_INTERVAL
from . import DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up GeckoTerminal sensors based on config entry."""
    _LOGGER.debug(f"Setting up sensor for GeckoTerminal entry: {entry.data}")
    
    # Pobierz dane z konfiguracji
    name = entry.data[CONF_NAME]
    network = entry.data[CONF_NETWORK]
    pool_address = entry.data[CONF_POOL_ADDRESS]
    
    # Pobierz opcje z konfiguracji lub użyj domyślnych wartości
    show_volume = entry.data.get(CONF_SHOW_VOLUME, True)
    decimal_places = entry.data.get(CONF_DECIMAL_PLACES, 2)
    show_fdv = entry.data.get(CONF_SHOW_FDV, True)
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    
    # Utwórz i dodaj sensor
    sensor = GeckoTerminalSensor(
        hass, 
        entry.entry_id, 
        name, 
        network, 
        pool_address, 
        show_volume, 
        decimal_places, 
        show_fdv,
        update_interval
    )
    async_add_entities([sensor], True)

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

def format_price(price_str, decimal_places):
    """Format price with specified decimal places."""
    try:
        price_float = float(price_str)
        return round(price_float, decimal_places)
    except (ValueError, TypeError):
        return price_str

def format_fdv(fdv_str):
    """Format FDV to more readable format."""
    try:
        fdv_float = float(fdv_str)
        if fdv_float >= 1_000_000_000:  # Miliard+
            return f"{fdv_float / 1_000_000_000:.2f}mld"
        elif fdv_float >= 1_000_000:  # Milion+
            return f"{fdv_float / 1_000_000:.2f}mln"
        elif fdv_float >= 1_000:  # Tysiąc+
            return f"{fdv_float / 1_000:.2f}tys"
        else:
            return f"{fdv_float:.2f}"
    except (ValueError, TypeError):
        return fdv_str

class GeckoTerminalSensor(SensorEntity):
    """Representation of a GeckoTerminal sensor."""

    def __init__(self, hass, entry_id, name, network, pool_address, 
                 show_volume=True, decimal_places=2, show_fdv=True,
                 update_interval=DEFAULT_UPDATE_INTERVAL):
        """Initialize the sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._name = name
        self._network = network
        self._pool_address = pool_address
        self._show_volume = show_volume
        self._decimal_places = decimal_places
        self._show_fdv = show_fdv
        self._update_interval = update_interval
        self._state = None
        self._attrs = {}
        self._available = True
        self._attr_native_unit_of_measurement = "USD"
        
        # Unikalny ID dla sensora
        self._attr_unique_id = f"{DOMAIN}_{network}_{pool_address}"
        
        # Informacje o urządzeniu
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": f"{name} ({network})",
            "manufacturer": "GeckoTerminal",
            "model": f"Pool: {pool_address}",
            "sw_version": "1.2.0",
            "via_device": (DOMAIN, network),
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._state is None:
            return None
        return format_price(self._state, self._decimal_places)

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:currency-usd"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def available(self):
        """Return if entity is available."""
        return self._available
        
    @property
    def scan_interval(self):
        """Return the scan interval for this entity."""
        return timedelta(seconds=self._update_interval)

    async def async_update(self):
        """Fetch new state data for the sensor."""
        _LOGGER.debug(f"Aktualizacja sensora GeckoTerminal dla sieci: {self._network}, puli: {self._pool_address}")
        
        url = f"https://api.geckoterminal.com/api/v2/networks/{self._network}/pools/{self._pool_address}"
        try:
            async with async_timeout.timeout(10):
                response = await self.hass.async_add_executor_job(
                    self._fetch_data, url
                )
                
            if not response:
                _LOGGER.error("Brak odpowiedzi z GeckoTerminal API")
                self._available = False
                return
                
            self._available = True
            
            if "data" in response and "attributes" in response["data"]:
                attributes = response["data"]["attributes"]
                
                # Ustaw stan sensora (cena)
                if "base_token_price_usd" in attributes:
                    self._state = attributes["base_token_price_usd"]
                
                # Pobierz podstawowe informacje
                base_token_symbol = attributes.get("base_token_symbol", "")
                quote_token_symbol = attributes.get("quote_token_symbol", "")
                
                # Dodaj podstawowe atrybuty
                self._attrs["base_token_symbol"] = base_token_symbol
                self._attrs["quote_token_symbol"] = quote_token_symbol
                self._attrs["pool_name"] = attributes.get("name", f"{base_token_symbol}/{quote_token_symbol}")
                self._attrs["pool_address"] = self._pool_address
                self._attrs["update_interval"] = f"{self._update_interval} s"
                
                # Dodaj zmianę ceny, jeśli dostępna
                if "price_change_percentage" in attributes:
                    price_changes = attributes["price_change_percentage"]
                    for period, value in price_changes.items():
                        self._attrs[f"price_change_{period}"] = f"{value}%"
                
                # Dodaj wolumen 24h, jeśli opcja włączona
                if self._show_volume and "volume_usd" in attributes and "h24" in attributes["volume_usd"]:
                    volume_24h = attributes["volume_usd"]["h24"]
                    self._attrs["volume_24h"] = format_fdv(volume_24h)
                
                # Dodaj FDV (Fully Diluted Valuation), jeśli opcja włączona
                if self._show_fdv and "fdv_usd" in attributes:
                    fdv = attributes["fdv_usd"]
                    self._attrs["fdv"] = format_fdv(fdv)
                
                # Dodaj informację o czasie ostatniej aktualizacji
                self._attrs["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Sprawdź, czy udało się ustawić stan
                if "base_token_price_usd" not in attributes:
                    _LOGGER.error(f"Nieprawidłowa struktura danych z API GeckoTerminal: brak base_token_price_usd")
                    self._state = None
            else:
                _LOGGER.error(f"Nieprawidłowa struktura danych z API GeckoTerminal: brak data lub attributes")
                self._state = None
                self._available = False
        except Exception as e:
            _LOGGER.error(f"Błąd pobierania danych z GeckoTerminal: {e}")
            self._state = None
            self._available = False

    def _fetch_data(self, url):
        """Fetch data from API."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            _LOGGER.error(f"Błąd pobierania danych: {e}")
            return None