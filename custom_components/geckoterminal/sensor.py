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
    
    # Tworzymy źródło danych, które będzie współdzielone przez wszystkie sensory
    data_source = GeckoTerminalDataSource(hass, network, pool_address, update_interval)
    
    entities = []
    
    # Główny sensor ceny
    price_sensor = GeckoTerminalPriceSensor(
        data_source, 
        entry.entry_id, 
        name, 
        network, 
        pool_address, 
        decimal_places
    )
    entities.append(price_sensor)
    
    # Sensor ceny z określoną liczbą miejsc po przecinku
    formatted_price_sensor = GeckoTerminalFormattedPriceSensor(
        data_source,
        entry.entry_id,
        name,
        network,
        pool_address,
        decimal_places
    )
    entities.append(formatted_price_sensor)
    
    # Sensor wolumenu 24h, jeśli opcja włączona
    if show_volume:
        volume_sensor = GeckoTerminalVolumeSensor(
            data_source,
            entry.entry_id,
            name,
            network,
            pool_address
        )
        entities.append(volume_sensor)
    
    # Sensor FDV, jeśli opcja włączona
    if show_fdv:
        fdv_sensor = GeckoTerminalFDVSensor(
            data_source,
            entry.entry_id,
            name,
            network,
            pool_address
        )
        entities.append(fdv_sensor)
    
    # Dodajemy encje dopiero po ich całkowitej inicjalizacji
    async_add_entities(entities, True)

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
        # Upewnij się, że price_str jest liczbą zmiennoprzecinkową
        price_float = float(price_str)
        # Formatuj cenę z określoną liczbą miejsc po przecinku
        formatted_price = round(price_float, decimal_places)
        # Upewnij się, że zawsze wyświetla się dokładnie decimal_places cyfr po przecinku
        return '{:.{prec}f}'.format(formatted_price, prec=decimal_places)
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

class GeckoTerminalDataSource:
    """Data source for GeckoTerminal sensors."""
    
    def __init__(self, hass, network, pool_address, update_interval):
        """Initialize the data source."""
        self.hass = hass
        self._network = network
        self._pool_address = pool_address
        self._update_interval = update_interval
        self._data = None
        self._last_update = None
        self._available = True
        self._listeners = []
    
    @property
    def available(self):
        """Return if data source is available."""
        return self._available
    
    @property
    def data(self):
        """Return the data."""
        return self._data
    
    @property
    def scan_interval(self):
        """Return the scan interval."""
        return timedelta(seconds=self._update_interval)
    
    def register_listener(self, listener):
        """Register a listener."""
        self._listeners.append(listener)
    
    async def async_update(self):
        """Fetch new state data for all sensors."""
        _LOGGER.debug(f"Aktualizacja danych GeckoTerminal dla sieci: {self._network}, puli: {self._pool_address}")
        
        # Sprawdź, czy minął czas od ostatniej aktualizacji
        now = datetime.now()
        if (self._last_update is not None and 
            (now - self._last_update) < timedelta(seconds=self._update_interval)):
            _LOGGER.debug("Pomijam aktualizację, zbyt krótki czas od ostatniej aktualizacji")
            return
        
        url = f"https://api.geckoterminal.com/api/v2/networks/{self._network}/pools/{self._pool_address}"
        try:
            async with async_timeout.timeout(10):
                response = await self.hass.async_add_executor_job(
                    self._fetch_data, url
                )
                
            if not response:
                _LOGGER.error("Brak odpowiedzi z GeckoTerminal API")
                self._available = False
                self._notify_listeners()
                return
                
            self._available = True
            
            if "data" in response and "attributes" in response["data"]:
                self._data = response["data"]["attributes"]
                self._last_update = now
                _LOGGER.debug(f"Dane zaktualizowane pomyślnie, dostępne atrybuty: {list(self._data.keys())}")
            else:
                _LOGGER.error(f"Nieprawidłowa struktura danych z API GeckoTerminal: brak data lub attributes")
                self._available = False
            
            self._notify_listeners()
                
        except Exception as e:
            _LOGGER.error(f"Błąd pobierania danych z GeckoTerminal: {e}")
            self._available = False
            self._notify_listeners()

    def _fetch_data(self, url):
        """Fetch data from API."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            _LOGGER.error(f"Błąd pobierania danych: {e}")
            return None
    
    def _notify_listeners(self):
        """Notify all listeners about a data update."""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                _LOGGER.error(f"Błąd podczas powiadamiania słuchacza: {e}")

class GeckoTerminalBaseSensor(SensorEntity):
    """Base class for GeckoTerminal sensors."""
    
    def __init__(self, data_source, entry_id, name, network, pool_address, suffix=""):
        """Initialize the sensor."""
        super().__init__()
        self._data_source = data_source
        self.hass = data_source.hass
        self._entry_id = entry_id
        self._name = f"{name}{suffix}"
        self._network = network
        self._pool_address = pool_address
        self._state = None
        self._attrs = {}
        
        # Unikalny ID dla sensora
        self._attr_unique_id = f"{DOMAIN}_{network}_{pool_address}_{suffix.lower().replace(' ', '_')}"
        
        # Informacje o urządzeniu
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{DOMAIN}_{network}_{pool_address}")},
            "name": f"{name} ({network})",
            "manufacturer": "GeckoTerminal",
            "model": f"Pool: {pool_address}",
            "sw_version": "1.3.0",
            "via_device": (DOMAIN, network),
        }
        
        # Zarejestruj sensor jako słuchacza aktualizacji danych
        data_source.register_listener(self._handle_data_update)
    
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name
    
    @property
    def available(self):
        """Return if entity is available."""
        return self._data_source.available
    
    @property
    def scan_interval(self):
        """Return the scan interval for this entity."""
        return self._data_source.scan_interval
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attrs
    
    def _handle_data_update(self):
        """Handle data update from the data source."""
        try:
            # Sprawdź, czy hass jest dostępny przed wywołaniem async_write_ha_state
            if hasattr(self, 'hass') and self.hass is not None:
                self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Błąd podczas aktualizacji stanu encji: {e}")
    
    async def async_update(self):
        """Fetch new state data for the sensor."""
        await self._data_source.async_update()

class GeckoTerminalPriceSensor(GeckoTerminalBaseSensor):
    """Representation of a GeckoTerminal price sensor."""
    
    def __init__(self, data_source, entry_id, name, network, pool_address, decimal_places):
        """Initialize the sensor."""
        super().__init__(data_source, entry_id, name, network, pool_address)
        self._decimal_places = decimal_places
        self._attr_native_unit_of_measurement = "USD"
    
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:currency-usd"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._data_source.data is None:
            return None
        
        price = self._data_source.data.get("base_token_price_usd")
        if price is None:
            return None
        
        # Pobierz podstawowe informacje
        base_token_symbol = self._data_source.data.get("base_token_symbol", "")
        quote_token_symbol = self._data_source.data.get("quote_token_symbol", "")
        
        # Dodaj podstawowe atrybuty
        self._attrs["base_token_symbol"] = base_token_symbol
        self._attrs["quote_token_symbol"] = quote_token_symbol
        self._attrs["pool_name"] = self._data_source.data.get("name", f"{base_token_symbol}/{quote_token_symbol}")
        self._attrs["pool_address"] = self._pool_address
        
        # Dodaj zmianę ceny, jeśli dostępna
        if "price_change_percentage" in self._data_source.data:
            price_changes = self._data_source.data["price_change_percentage"]
            for period, value in price_changes.items():
                self._attrs[f"price_change_{period}"] = f"{value}%"
        
        # Dodaj informację o czasie ostatniej aktualizacji
        self._attrs["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return price

class GeckoTerminalFormattedPriceSensor(GeckoTerminalBaseSensor):
    """Representation of a GeckoTerminal formatted price sensor."""
    
    def __init__(self, data_source, entry_id, name, network, pool_address, decimal_places):
        """Initialize the sensor."""
        super().__init__(data_source, entry_id, name, network, pool_address, " Cena Sformatowana")
        self._decimal_places = decimal_places
        self._attr_native_unit_of_measurement = "USD"
    
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:currency-usd-circle"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._data_source.data is None:
            return None
        
        price = self._data_source.data.get("base_token_price_usd")
        if price is None:
            return None
        
        # Dodaj informację o liczbie miejsc po przecinku
        self._attrs["decimal_places"] = self._decimal_places
        
        # Formatuj cenę z określoną liczbą miejsc po przecinku
        try:
            return format_price(price, self._decimal_places)
        except Exception as e:
            _LOGGER.error(f"Błąd formatowania ceny: {e}")
            return None

class GeckoTerminalVolumeSensor(GeckoTerminalBaseSensor):
    """Representation of a GeckoTerminal volume sensor."""
    
    def __init__(self, data_source, entry_id, name, network, pool_address):
        """Initialize the sensor."""
        super().__init__(data_source, entry_id, name, network, pool_address, " Wolumen 24h")
        self._attr_native_unit_of_measurement = "USD"
    
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:chart-line"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._data_source.data is None:
            return None
        
        # Pobierz wolumen 24h
        if "volume_usd" in self._data_source.data and "h24" in self._data_source.data["volume_usd"]:
            volume_24h = self._data_source.data["volume_usd"]["h24"]
            self._attrs["formatted_volume"] = format_fdv(volume_24h)
            return float(volume_24h)
        
        return None

class GeckoTerminalFDVSensor(GeckoTerminalBaseSensor):
    """Representation of a GeckoTerminal FDV sensor."""
    
    def __init__(self, data_source, entry_id, name, network, pool_address):
        """Initialize the sensor."""
        super().__init__(data_source, entry_id, name, network, pool_address, " FDV")
        self._attr_native_unit_of_measurement = "USD"
    
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:cash-multiple"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._data_source.data is None:
            return None
        
        # Pobierz FDV
        if "fdv_usd" in self._data_source.data:
            fdv = self._data_source.data["fdv_usd"]
            self._attrs["formatted_fdv"] = format_fdv(fdv)
            return float(fdv)
        
        return None