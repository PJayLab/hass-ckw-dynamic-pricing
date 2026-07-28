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
4. Configure the CKW API URL parameters and thresholds:
   - API URL
   - Tariff name
   - Tariff type
   - Low price threshold (CHF/kWh)
   - High price threshold (CHF/kWh)

The integration calculates the required date parameters automatically for today and tomorrow.

## Entities

The integration creates these entities:

- Current price
- Minimum price
- Maximum price
- Average price
- All prices, with the normalized price list as attributes
- Below low price threshold
- Above high price threshold
