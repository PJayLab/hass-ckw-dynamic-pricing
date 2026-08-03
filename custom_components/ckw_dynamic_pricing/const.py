"""Constants for the CKW Dynamic Pricing integration."""

from datetime import timedelta

DOMAIN = "ckw_dynamic_pricing"
PLATFORMS = ["sensor", "binary_sensor"]
SCAN_INTERVAL = timedelta(hours=6)

DEFAULT_API_URL = (
    "https://e-ckw-public-data.de-c1.eu1.cloudhub.io/api/v1/"
    "netzinformationen/energie/dynamische-preise"
)
DEFAULT_TARIFF_NAMES = ["home_dynamic", "business_dynamic"]
DEFAULT_TARIFF_TYPE = "integrated"
DEFAULT_LOW_PRICE_THRESHOLD = 0.15
DEFAULT_HIGH_PRICE_THRESHOLD = 0.25

# Kept for backwards compatibility with existing config entries.  These fields are
# deliberately no longer presented in the UI: CKW's public endpoint and the
# all-inclusive ("integrated") price are now always used.
CONF_API_URL = "api_url"
CONF_TARIFF_NAME = "tariff_name"
CONF_TARIFF_TYPE = "tariff_type"
CONF_LOW_PRICE_THRESHOLD = "low_price_threshold"
CONF_HIGH_PRICE_THRESHOLD = "high_price_threshold"

LEGACY_CONF_PRICE_THRESHOLD = "price_threshold"
LEGACY_CONF_NETZEBENE = "netzebene"
