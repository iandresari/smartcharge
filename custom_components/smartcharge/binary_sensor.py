"""Binary sensor entities for EnBW Charging integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_ADDRESS,
    ATTR_EVSE_ID,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_STATUS,
    CONF_CHARGING_STATIONS,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    DOMAIN,
    STATUS_ICONS,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    charging_stations = entry.data.get(CONF_CHARGING_STATIONS, [])

    for station in charging_stations:
        station_id = station.get(CONF_STATION_ID)
        station_name = station.get(CONF_STATION_NAME)

        if not station_id:
            continue

        station_data = coordinator.data.get("chargePoints", {}).get(station_id)

        if station_data:
            charge_points = station_data.get("chargePoints", [])

            for charge_point in charge_points:
                evse_id = charge_point.get("evseId")
                if evse_id:
                    entities.append(
                        ChargePointAvailabilityBinarySensor(
                            coordinator,
                            station_id,
                            station_name,
                            evse_id,
                            charge_point.get("evse", {}).get("name", evse_id),
                        )
                    )
                    entities.append(
                        ChargePointOccupiedBinarySensor(
                            coordinator,
                            station_id,
                            station_name,
                            evse_id,
                            charge_point.get("evse", {}).get("name", evse_id),
                        )
                    )

    async_add_entities(entities)


class ChargePointAvailabilityBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for charge point availability."""

    _attr_has_entity_name = True
    _attr_device_class = "connectivity"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        station_id: str,
        station_name: str,
        evse_id: str,
        evse_name: str,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator)
        self.station_id = station_id
        self.station_name = station_name
        self.evse_id = evse_id
        self.evse_name = evse_name

        self._attr_unique_id = f"{station_id}_{evse_id}_available"
        self._attr_name = f"{station_name} - {evse_name} Available"

    @property
    def is_on(self) -> bool:
        """Return True if charge point is available."""
        station_data = self.coordinator.data.get("chargePoints", {}).get(
            self.station_id
        )

        if not station_data:
            return False

        charge_points = station_data.get("chargePoints", [])
        for cp in charge_points:
            if cp.get("evseId") == self.evse_id:
                status = cp.get("status", "")
                return status == "Available"

        return False

    @property
    def icon(self) -> str:
        """Return icon based on status."""
        if self.is_on:
            return "mdi:ev-station"
        else:
            return "mdi:ev-station-unavailable"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        station_data = self.coordinator.data.get("chargePoints", {}).get(
            self.station_id
        )

        if not station_data:
            return {}

        charge_points = station_data.get("chargePoints", [])
        for cp in charge_points:
            if cp.get("evseId") == self.evse_id:
                location = cp.get("location", {})
                status = cp.get("status", STATE_UNKNOWN)
                return {
                    ATTR_EVSE_ID: self.evse_id,
                    ATTR_STATUS: status,
                    ATTR_LATITUDE: location.get("latitude"),
                    ATTR_LONGITUDE: location.get("longitude"),
                    ATTR_ADDRESS: location.get("address"),
                    "icon": STATUS_ICONS.get(status.lower(), "mdi:help"),
                }

        return {}


class ChargePointOccupiedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for charge point occupied status."""

    _attr_has_entity_name = True
    _attr_device_class = "occupancy"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        station_id: str,
        station_name: str,
        evse_id: str,
        evse_name: str,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator)
        self.station_id = station_id
        self.station_name = station_name
        self.evse_id = evse_id
        self.evse_name = evse_name

        self._attr_unique_id = f"{station_id}_{evse_id}_occupied"
        self._attr_name = f"{station_name} - {evse_name} Occupied"

    @property
    def is_on(self) -> bool:
        """Return True if charge point is occupied."""
        station_data = self.coordinator.data.get("chargePoints", {}).get(
            self.station_id
        )

        if not station_data:
            return False

        charge_points = station_data.get("chargePoints", [])
        for cp in charge_points:
            if cp.get("evseId") == self.evse_id:
                status = cp.get("status", "")
                return status == "Occupied"

        return False

    @property
    def icon(self) -> str:
        """Return icon based on occupancy."""
        return "mdi:ev-station" if self.is_on else "mdi:ev-station-unavailable"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        station_data = self.coordinator.data.get("chargePoints", {}).get(
            self.station_id
        )

        if not station_data:
            return {}

        charge_points = station_data.get("chargePoints", [])
        for cp in charge_points:
            if cp.get("evseId") == self.evse_id:
                location = cp.get("location", {})
                return {
                    ATTR_EVSE_ID: self.evse_id,
                    ATTR_STATUS: cp.get("status"),
                    ATTR_LATITUDE: location.get("latitude"),
                    ATTR_LONGITUDE: location.get("longitude"),
                    ATTR_ADDRESS: location.get("address"),
                }

        return {}
