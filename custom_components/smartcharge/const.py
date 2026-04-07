"""Constants for the SmartCharge integration."""

from typing import Final

DOMAIN: Final = "smartcharge"
VERSION: Final = "1.0.1"

# API Configuration
API_BASE_URL: Final = "https://enbw-emp.azure-api.net/emobility-public-api/api/v1"
API_SUBSCRIPTION_KEY: Final = "d4954e8b2e444fc89a89a463788c0a72"
API_HEADERS: Final = {
    "User-Agent": "Home Assistant / EnBW Charging Integration",
    "Ocp-Apim-Subscription-Key": API_SUBSCRIPTION_KEY,
    "Referer": "https://www.enbw.com/",
    "Origin": "https://www.enbw.com",
}

# Configuration
CONF_CHARGING_STATIONS: Final = "charging_stations"
CONF_STATION_ID: Final = "station_id"
CONF_STATION_NAME: Final = "station_name"
CONF_UPDATE_INTERVAL: Final = "update_interval"

# Defaults
DEFAULT_UPDATE_INTERVAL: Final = 300  # 5 minutes

# Status mapping
CHARGE_POINT_STATUS = {
    "Available": "available",
    "Occupied": "occupied",
    "Faulted": "faulted",
    "Unavailable": "unavailable",
    "Reserved": "reserved",
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
ATTR_STATUS: Final = "status"
ATTR_LAST_UPDATE: Final = "last_update"
ATTR_EVSE_ID: Final = "evse_id"
ATTR_POWER_KW: Final = "power_kw"
ATTR_CONNECTOR_TYPE: Final = "connector_type"

# Entity categories
ENTITY_CATEGORY_OCCUPANCY: Final = "occupancy"
ENTITY_CATEGORY_INFO: Final = "diagnostic"

# Service names
SERVICE_ADD_CHARGING_POINT: Final = "add_charging_point"
SERVICE_REMOVE_CHARGING_POINT: Final = "remove_charging_point"
SERVICE_REFRESH_DATA: Final = "refresh_data"

# Platform names
PLATFORM_SENSOR: Final = "sensor"
PLATFORM_BINARY_SENSOR: Final = "binary_sensor"
