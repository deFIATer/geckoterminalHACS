import requests
from homeassistant.const import CURRENCY_USD
from homeassistant.helpers.entity import Entity
from . import CONF_NAME, CONF_NETWORK, CONF_POOL_ADDRESS

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return

    name = discovery_info[CONF_NAME]
    network = discovery_info[CONF_NETWORK]
    pool_address = discovery_info[CONF_POOL_ADDRESS]

    async_add_entities([GeckoTerminalSensor(name, network, pool_address)])

class GeckoTerminalSensor(Entity):
    def __init__(self, name, network, pool_address):
        self._name = name
        self._network = network
        self._pool_address = pool_address
        self._state = None
        self._unit_of_measurement = CURRENCY_USD

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    def update(self):
        url = f"https://api.geckoterminal.com/api/v2/networks/{self._network}/pools/{self._pool_address}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            self._state = data["data"]["attributes"]["base_token_price_usd"]
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to fetch data from GeckoTerminal: {e}")