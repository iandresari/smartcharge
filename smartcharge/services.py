"""Services for EnBW Charging integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_CHARGING_STATIONS,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    DOMAIN,
    SERVICE_ADD_CHARGING_POINT,
    SERVICE_REFRESH_DATA,
    SERVICE_REMOVE_CHARGING_POINT,
)
from .coordinator import EnBWChargingCoordinator

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for EnBW Charging."""

    async def handle_add_charging_point(call: ServiceCall) -> None:
        """Handle adding a new charging point."""
        station_id = call.data.get(CONF_STATION_ID)
        station_name = call.data.get(CONF_STATION_NAME)

        if not station_id or not station_name:
            _LOGGER.error("Missing station_id or station_name")
            return

        # Find the integration entry
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, EnBWChargingCoordinator):
                current_stations = coordinator.entry.data.get(
                    CONF_CHARGING_STATIONS, []
                )

                # Check if already exists
                if any(
                    s.get(CONF_STATION_ID) == station_id
                    for s in current_stations
                ):
                    _LOGGER.warning("Station %s already exists", station_id)
                    return

                # Add new station
                current_stations.append(
                    {
                        CONF_STATION_ID: station_id,
                        CONF_STATION_NAME: station_name,
                    }
                )

                hass.config_entries.async_update_entry(
                    coordinator.entry,
                    data={
                        **coordinator.entry.data,
                        CONF_CHARGING_STATIONS: current_stations,
                    },
                )

                await coordinator.async_refresh()
                _LOGGER.info(
                    "Added charging station %s (%s)", station_id, station_name
                )
                return

    async def handle_remove_charging_point(call: ServiceCall) -> None:
        """Handle removing a charging point."""
        station_id = call.data.get(CONF_STATION_ID)

        if not station_id:
            _LOGGER.error("Missing station_id")
            return

        # Find the integration entry
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, EnBWChargingCoordinator):
                current_stations = coordinator.entry.data.get(
                    CONF_CHARGING_STATIONS, []
                )

                # Remove station
                updated_stations = [
                    s
                    for s in current_stations
                    if s.get(CONF_STATION_ID) != station_id
                ]

                if len(updated_stations) == len(current_stations):
                    _LOGGER.warning("Station %s not found", station_id)
                    return

                hass.config_entries.async_update_entry(
                    coordinator.entry,
                    data={
                        **coordinator.entry.data,
                        CONF_CHARGING_STATIONS: updated_stations,
                    },
                )

                await coordinator.async_refresh()
                _LOGGER.info("Removed charging station %s", station_id)
                return

    async def handle_refresh_data(call: ServiceCall) -> None:
        """Handle manual data refresh."""
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, EnBWChargingCoordinator):
                await coordinator.async_refresh()
                _LOGGER.info("Manually refreshed charging station data")

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_CHARGING_POINT,
        handle_add_charging_point,
        schema={
            "type": "object",
            "properties": {
                CONF_STATION_ID: {
                    "type": "string",
                    "description": "Station ID",
                },
                CONF_STATION_NAME: {
                    "type": "string",
                    "description": "Station display name",
                },
            },
            "required": [
                CONF_STATION_ID,
                CONF_STATION_NAME,
            ],
        },
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_CHARGING_POINT,
        handle_remove_charging_point,
        schema={
            "type": "object",
            "properties": {
                CONF_STATION_ID: {
                    "type": "string",
                    "description": "Station ID",
                },
            },
            "required": [CONF_STATION_ID],
        },
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DATA,
        handle_refresh_data,
    )

    _LOGGER.debug("EnBW Charging services registered")
