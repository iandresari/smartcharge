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
CONF_STATIC_FRIENDLY_NAME: Final = "static_friendly_name"
CONF_AUTO_API_KEY: Final = "auto_api_key"
CONF_MANUAL_API_KEY: Final = "manual_api_key"
CONF_TARIFF_PRICE_PER_KWH: Final = "tariff_price_ct_per_kwh"
CONF_TARIFF_BASE_FEE: Final = "tariff_base_fee_ct"
CONF_ODOMETER_ENTITY: Final = "odometer_entity"

# New entry-type config keys
CONF_CO2_ENTITY: Final = "co2_entity"
CONF_PRICE_ENTITY: Final = "price_entity"
CONF_CAR_ENTRY_ID: Final = "car_entry_id"
CONF_ODOMETER_SNAPSHOT: Final = "odometer_snapshot"
CONF_AUTO_DISCOVERY: Final = "auto_discovery"
CONF_STATION_LAT: Final = "station_lat"
CONF_STATION_LON: Final = "station_lon"

# Entry type identifiers
ENTRY_TYPE_CAR: Final = "car"
ENTRY_TYPE_STATION: Final = "station"
ENTRY_TYPE_TEMPORARY: Final = "temporary_station"
ENTRY_TYPE_WALLBOX: Final = "wallbox"

# Defaults
DEFAULT_UPDATE_INTERVAL: Final = 300  # 5 minutes
DEFAULT_AUTO_API_KEY: Final = True
DEFAULT_TARIFF_BASE_FEE: Final = 0
DEFAULT_AUTO_DISCOVERY: Final = False

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

# Persistent storage version (increment when the stored schema changes)
STORAGE_VERSION: Final = 1

# Platform names
PLATFORM_SENSOR: Final = "sensor"
