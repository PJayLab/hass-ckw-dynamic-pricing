"""Constants for the CKW Dynamic Pricing integration."""

from datetime import timedelta

DOMAIN = "ckw_dynamic_pricing"
PLATFORMS = ["sensor", "binary_sensor", "button"]
SCAN_INTERVAL = timedelta(hours=6)

DEFAULT_API_URL = (
    "https://e-ckw-public-data.de-c1.eu1.cloudhub.io/api/v1/"
    "netzinformationen/energie/dynamische-preise"
)
DEFAULT_TARIFF_NAMES = ["home_dynamic", "business_dynamic"]
TARIFF_LABELS = {
    "home_dynamic": "Home Dynamic",
    "business_dynamic": "Business Dynamic",
}
DEFAULT_TARIFF_TYPE = "integrated"
DEFAULT_LOW_PRICE_THRESHOLD = 0.15
DEFAULT_HIGH_PRICE_THRESHOLD = 0.25

CONF_TARIFF_NAME = "tariff_name"
CONF_TARIFF_TYPE = "tariff_type"
CONF_LOW_PRICE_THRESHOLD = "low_price_threshold"
CONF_HIGH_PRICE_THRESHOLD = "high_price_threshold"

LEGACY_CONF_PRICE_THRESHOLD = "price_threshold"
