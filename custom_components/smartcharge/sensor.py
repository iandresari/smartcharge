"""Sensor entities for EnBW Charging integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_ADDRESS,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_OCCUPANCY_HOURLY,
    ATTR_OCCUPANCY_WEEKDAY,
    CHARGE_POINT_STATUS,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    CONF_TARIFF_PRICE_PER_KWH,
    CONF_TARIFF_BASE_FEE,
    DOMAIN,
    STATUS_ICONS,
)
from .car_sensor import (
    CarAccumCO2Sensor,
    CarAccumCostSensor,
    CarAccumEnergySensor,
    CarChargingSensor,
    CarCO2PerKmSensor,
    CarCostPerKmSensor,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    if entry.data.get("entry_type") == "car":
        main = CarChargingSensor(hass, entry)
        children = [
            CarAccumEnergySensor(main, entry),
            CarAccumCO2Sensor(main, entry),
            CarAccumCostSensor(main, entry),
            CarCO2PerKmSensor(main, entry),
            CarCostPerKmSensor(main, entry),
        ]
        main.register_children(children)
        async_add_entities([main, *children])
        return

    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    station_id = entry.data.get(CONF_STATION_ID)
    station_name = entry.data.get(CONF_STATION_NAME)

    if not station_id:
        return

    # Get static friendly name from config entry if present
    static_friendly_name = entry.data.get("static_friendly_name")
    async_add_entities(
        [
            StationAvailabilitySensor(
                coordinator,
                station_id,
                station_name,
                static_friendly_name,
            )
        ]
    )


class StationAvailabilitySensor(CoordinatorEntity, SensorEntity):
    """
    Single sensor per station showing availability,
    charge point details & histogram.

    The state value is the count of available charge points.
    The friendly name dynamically reflects availability,
    e.g. "2 / 5 - StationName".
    Attributes include every charge point's status, GPS, address,
    connector info, and the hourly / weekday occupancy histograms.
    """

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        station_id: str,
        station_name: str,
        static_friendly_name: str | None = None,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.station_id = station_id
        _station_name = station_name or f"Station_{station_id}"
        self.static_friendly_name = static_friendly_name or _station_name

        self._attr_unique_id = f"{station_id}_availability"
        self.entity_id = f"sensor.sc_station_{station_id}"

    def _get_counts(self) -> tuple[int, int]:
        """Return (available, total) charge point counts."""
        if not self.coordinator.data:
            return 0, 0
        charge_points = self.coordinator.data.get("chargePoints", [])
        total = len(charge_points)
        available = sum(1 for cp in charge_points if cp.get("status") == "AVAILABLE")
        return available, total

    @property
    def name(self) -> str:
        """Return dynamic name showing availability."""
        available, total = self._get_counts()
        if total > 9 or available > 9:
            available_str = " ".join(str(available))
        else:
            available_str = str(available)
        return f"{available_str} / {total} - {self.static_friendly_name}"

    @property
    def icon(self) -> str:
        """Return icon based on availability."""
        available, total = self._get_counts()
        if total == 0 or available == 0:
            return STATUS_ICONS["occupied"]
        return STATUS_ICONS["available"]

    @property
    def native_value(self) -> StateType:
        """Return 'available' if any charge point is free, otherwise 'occupied'."""
        available, total = self._get_counts()
        if total == 0:
            return "unknown"
        return "available" if available > 0 else "occupied"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return station info, all charge point details, and occupancy histograms."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data
        charge_points = data.get("chargePoints", [])
        available, total = self._get_counts()

        attrs: dict[str, Any] = {
            "total_charge_points": total,
            "available_count": available,
            "occupied_count": sum(
                1 for cp in charge_points if cp.get("status") == "OCCUPIED"
            ),
            ATTR_LATITUDE: data.get("lat"),
            ATTR_LONGITUDE: data.get("lon"),
            ATTR_ADDRESS: data.get("shortAddress"),
        }

        # Expose each charge point's status and details
        for cp in charge_points:
            evse_id = cp.get("evseId", "unknown")
            raw_status = cp.get("status", "UNKNOWN")
            friendly_status = CHARGE_POINT_STATUS.get(raw_status, raw_status)
            connectors = cp.get("connectors", [])
            connector = connectors[0] if connectors else {}
            power = connector.get("maxPowerInKw")
            plug = connector.get("plugTypeName")
            detail = friendly_status
            if power:
                detail += f" | {power} kW"
            if plug:
                detail += f" | {plug}"
            attrs[evse_id] = detail

        # Occupancy histograms (previously on the separate occupancy sensor)
        attrs[ATTR_OCCUPANCY_WEEKDAY] = self.coordinator.get_occupancy_by_weekday()
        attrs[ATTR_OCCUPANCY_HOURLY] = self.coordinator.get_occupancy_by_hour()

        # Tariff
        options = self.coordinator.entry.options
        tariff_price = options.get(CONF_TARIFF_PRICE_PER_KWH)
        tariff_base = options.get(CONF_TARIFF_BASE_FEE, 0)
        if tariff_price is not None:
            attrs["tariff_price_ct_per_kwh"] = tariff_price
            attrs["tariff_base_fee_ct"] = tariff_base

        return attrs
