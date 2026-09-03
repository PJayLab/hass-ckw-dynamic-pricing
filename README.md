# CKW Dynamic Pricing

<img width="1024" height="1024" alt="ckwdynha" src="https://github.com/user-attachments/assets/0600ed86-c765-4169-866f-3e551da9f994" />

Home Assistant custom integration for CKW dynamic electricity prices.

## Installation with HACS

1. Open HACS → Integrations.
2. Add this repository as a custom repository: `https://github.com/PJayLab/hass-ckw-dynamic-pricing`.
3. Select the `Integration` category.
4. Search for `CKW Dynamic Pricing` and install it.
5. Restart Home Assistant.

## Configuration

1. Open Settings → Devices & services.
2. Select **Add integration**.
3. Search for **CKW Dynamic Pricing**.
4. Choose the CKW tariff and configure the price thresholds. You can add the integration again for the other tariff (Home Dynamic or Business Dynamic); each tariff gets its own device and entities.
   - Tariff name (Home or Business Dynamic)
   - The official CKW public API URL and all-inclusive tariff type are managed by the integration.
   - Low price threshold (CHF/kWh)
   - High price threshold (CHF/kWh)

The integration calculates the required date parameters automatically for today and tomorrow.

## Entities

The integration creates these entities:

- Current price
- Minimum price
- Maximum price
- Next price change
- Average price today and tomorrow (with min, max, median, percentiles and coverage attributes)
- Cheapest and most expensive 2- and 4-hour windows for today and tomorrow (disabled by default)
- All prices, with the normalized price list as attributes
- A **Refresh tariffs** button in the device's Configuration section
- A **Last API update** timestamp in the Diagnostic section
- Below low price threshold
- Above high price threshold
- Cheapest/most-expensive 10%, 25% and 50% price-slot sensors, plus 2- and 4-hour window-membership sensors (disabled by default)

Daily statistics roll over immediately after local midnight using the already-fetched tomorrow schedule; API polling remains on the normal six-hour interval.

Entity order follows a logical order: current price and next change, daily statistics, then the optional lowest/highest time windows and price-slot helpers. Optional planning and diagnostic entities are disabled by default and can be enabled from the entity registry.
