"""Constants for the SmartCharge integration."""

from typing import Final

DOMAIN: Final = "smartcharge"

# API Configuration
API_BASE_URL: Final = "https://enbw-emp.azure-api.net/emobility-public-api/api/v1"
API_MAP_URL: Final = (
    "https://www.enbw.com/elektromobilitaet/produkte/"
    "mobilityplus-app/ladestation-finden/map"
)
API_FALLBACK_SUBSCRIPTION_KEY: Final = "d4954e8b2e444fc89a89a463788c0a72"
API_HEADERS: Final = {
    "Accept": "application/json",
    "User-Agent": "Home Assistant / EnBW Charging Integration",
    "Referer": "https://www.enbw.com/",
    "Origin": "https://www.enbw.com",
}

# Configuration
CONF_STATION_ID: Final = "station_id"
CONF_STATION_NAME: Final = "station_name"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_AUTO_API_KEY: Final = "auto_api_key"
CONF_MANUAL_API_KEY: Final = "manual_api_key"

# Defaults
DEFAULT_UPDATE_INTERVAL: Final = 300  # 5 minutes
DEFAULT_AUTO_API_KEY: Final = True

# Status mapping (API returns uppercase values)
CHARGE_POINT_STATUS = {
    "AVAILABLE": "available",
    "OCCUPIED": "occupied",
    "FAULTED": "faulted",
    "UNAVAILABLE": "unavailable",
    "RESERVED": "reserved",
}

# Icon mapping based on status
STATUS_ICONS = {
    "available": "mdi:ev-station",
    "occupied": "mdi:ev-station-unavailable",
    "faulted": "mdi:alert-circle",
    "unavailable": "mdi:cancel",
    "reserved": "mdi:lock",
}

# Attribute keys
ATTR_LATITUDE: Final = "latitude"
ATTR_LONGITUDE: Final = "longitude"
ATTR_ADDRESS: Final = "address"
ATTR_OCCUPANCY_WEEKDAY: Final = "occupancy_weekday"
ATTR_OCCUPANCY_HOURLY: Final = "occupancy_hourly"

# Service names
SERVICE_REFRESH_DATA: Final = "refresh_data"

# Platform names
PLATFORM_SENSOR: Final = "sensor"
