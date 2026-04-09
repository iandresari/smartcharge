"""Device tracker entities for EnBW Charging station locations."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    CONF_CHARGING_STATIONS,
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
    """Set up device tracker entities for charging stations."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    charging_stations = entry.data.get(CONF_CHARGING_STATIONS, [])

    for station in charging_stations:
        station_id = station.get(CONF_STATION_ID)
        station_name = station.get(CONF_STATION_NAME)

        if not station_id:
            continue

        entities.append(ChargingStationTracker(coordinator, station_id, station_name))

    async_add_entities(entities)


class ChargingStationTracker(CoordinatorEntity, TrackerEntity):
    """Device tracker for a charging station location."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:ev-station"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        station_id: str,
        station_name: str,
    ) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator)
        self.station_id = station_id
        self.station_name = station_name

        self._attr_unique_id = f"{station_id}_location"
        self._attr_name = f"{station_name}"

    @property
    def _station_data(self) -> dict[str, Any] | None:
        """Return current station data from coordinator."""
        return self.coordinator.data.get("chargePoints", {}).get(self.station_id)

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude of the station."""
        data = self._station_data
        if data:
            location = data.get("location", {})
            return location.get("latitude")
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude of the station."""
        data = self._station_data
        if data:
            location = data.get("location", {})
            return location.get("longitude")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        attrs: dict[str, Any] = {
            "station_id": self.station_id,
        }

        data = self._station_data
        if data:
            # Address
            address = data.get("address", {})
            if address:
                street = address.get("street", "")
                city = address.get("city", "")
                attrs["address"] = ", ".join(filter(None, [street, city]))

            # Charge point summary
            charge_points = data.get("chargePoints", [])
            total = len(charge_points)
            available = sum(
                1 for cp in charge_points if cp.get("status") == "Available"
            )
            attrs["charge_points_total"] = total
            attrs["charge_points_available"] = available
            attrs["station_name"] = data.get("name", self.station_name)

        return attrs
