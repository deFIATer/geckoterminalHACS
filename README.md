# GeckoTerminal Integration for Home Assistant

Monitor token pool prices from [GeckoTerminal](https://www.geckoterminal.com) directly in Home Assistant!  
This custom integration fetches real-time data from the GeckoTerminal DEX API and creates sensors for your selected liquidity pools.

## 🔧 Features

- Create sensors for token pools by entering:
  - Sensor name
  - Network (e.g. `base`, `ethereum`, `arbitrum`, `abstract` or any other supported network)
  - Liquidity pool address
- Real-time token price in USD
- Configuration via Home Assistant UI (Config Flow)
- Editable options (network/pool address) via UI (Options Flow)
- Support for multiple sensors (add as many tokens as you want)
- Automatic data updates every 5 minutes
- Additional attributes:
  - Base and quote token symbols
  - Total liquidity in USD
  - Volume in USD
  - Price change percentage
  - And more

## 📦 Installation via HACS

1. Go to **HACS → Integrations → ⋯ → Custom Repositories**
2. Add this repository URL:
   ```
   https://github.com/deFIATer/geckoterminalHACS
   ```
   with category **Integration**
3. Find **GeckoTerminal** in the list and click **Install**
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration** and search for **GeckoTerminal**

## 📈 Example Use Case

You can add a sensor for a token pair like USDC/WETH on the Base network by entering:

- Network: `base`
- Pool address: `0x23a331e9bc1e2c08e44b6ce7f0c35f74b322e6ad`

The integration will create a sensor showing the current base token price in USD.

## 🌍 Language Support

The integration supports both English and Polish languages.

## 🔍 Troubleshooting

If you encounter issues:

1. Check that your network and pool address are correct
2. Review Home Assistant logs for detailed error messages
3. Try the pool address on GeckoTerminal website to ensure it exists

## 💬 Feedback & Contributions

Feel free to open issues or pull requests — contributions are very welcome!

---

**Author**: [@deFIATer](https://github.com/deFIATer)  
Based on the [GeckoTerminal API Guide](https://apiguide.geckoterminal.com)
