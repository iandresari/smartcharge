"""Sensor entities for EnBW Charging integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_ADDRESS,
    ATTR_EVSE_ID,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_OCCUPANCY_HOURLY,
    ATTR_OCCUPANCY_WEEKDAY,
    ATTR_STATUS,
    CHARGE_POINT_STATUS,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    DOMAIN,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    station_id = entry.data.get(CONF_STATION_ID)
    station_name = entry.data.get(CONF_STATION_NAME)

    if not station_id:
        return

    if coordinator.data:
        charge_points = coordinator.data.get("chargePoints", [])

        for cp in charge_points:
            evse_id = cp.get("evseId")
            if evse_id:
                entities.append(
                    ChargePointStatusSensor(
                        coordinator,
                        station_id,
                        station_name,
                        evse_id,
                        cp.get("evse", {}).get("name", evse_id),
                    )
                )

        entities.append(StationOccupancySensor(coordinator, station_id, station_name))

    async_add_entities(entities)


class ChargePointStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual charge point status."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:ev-station"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        station_id: str,
        station_name: str,
        evse_id: str,
        evse_name: str,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.station_id = station_id
        self.station_name = station_name
        self.evse_id = evse_id
        self.evse_name = evse_name

        self._attr_unique_id = f"{station_id}_{evse_id}_status"
        self._attr_name = f"{station_name} {evse_name}"

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return STATE_UNKNOWN

        charge_points = self.coordinator.data.get("chargePoints", [])
        for cp in charge_points:
            if cp.get("evseId") == self.evse_id:
                status = cp.get("status")
                return CHARGE_POINT_STATUS.get(status, status or STATE_UNKNOWN)

        return STATE_UNKNOWN

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}

        charge_points = self.coordinator.data.get("chargePoints", [])
        for cp in charge_points:
            if cp.get("evseId") == self.evse_id:
                location = cp.get("location", {})
                return {
                    ATTR_EVSE_ID: self.evse_id,
                    ATTR_STATUS: cp.get("status") or STATE_UNKNOWN,
                    ATTR_LATITUDE: location.get("latitude"),
                    ATTR_LONGITUDE: location.get("longitude"),
                    ATTR_ADDRESS: location.get("address"),
                    "power": cp.get("powerKw"),
                    "connector_type": cp.get("connectorType"),
                }

        return {}


class StationOccupancySensor(CoordinatorEntity, SensorEntity):
    """Sensor for station occupancy percentage."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:percent"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        station_id: str,
        station_name: str,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.station_id = station_id
        self.station_name = station_name

        self._attr_unique_id = f"{station_id}_occupancy"
        self._attr_name = f"{station_name} Occupancy"

    @property
    def native_value(self) -> StateType:
        """Return current occupancy percentage."""
        if not self.coordinator.data:
            return 0.0

        charge_points = self.coordinator.data.get("chargePoints", [])
        if not charge_points:
            return 0.0

        occupied = sum(1 for cp in charge_points if cp.get("status") == "Occupied")
        return round((occupied / len(charge_points)) * 100, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with occupancy history."""
        weekday_occupancy = self.coordinator.get_occupancy_by_weekday()
        hourly_occupancy = self.coordinator.get_occupancy_by_hour()

        return {
            ATTR_OCCUPANCY_WEEKDAY: weekday_occupancy,
            ATTR_OCCUPANCY_HOURLY: hourly_occupancy,
        }
