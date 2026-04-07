"""Data coordinator for EnBW Charging integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE_URL,
    API_HEADERS,
    CONF_CHARGING_STATIONS,
    CONF_STATION_ID,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


class EnBWChargingCoordinator(DataUpdateCoordinator):
    """Coordinator for EnBW Charging data."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        entry: ConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=DEFAULT_UPDATE_INTERVAL
            ),
        )
        self.session = session
        self.entry = entry
        self.occupancy_history: dict[str, list[dict[str, Any]]] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from EnBW API."""
        try:
            charging_stations = self.entry.data.get(CONF_CHARGING_STATIONS, [])

            if not charging_stations:
                _LOGGER.debug("No charging stations configured")
                return {"chargePoints": {}}

            chargePoints = {}

            for station in charging_stations:
                station_id = station.get(CONF_STATION_ID)
                if not station_id:
                    continue

                try:
                    data = await self._fetch_station_data(station_id)
                    if data:
                        chargePoints[station_id] = data
                        await self._update_occupancy_history(station_id, data)
                except Exception as err:
                    _LOGGER.error(
                        "Error fetching data for station %s: %s", station_id, err
                    )

            return {
                "chargePoints": chargePoints,
                "lastUpdate": dt_util.now(),
                "occupancyHistory": self.occupancy_history,
            }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with EnBW API: {err}") from err

    async def _fetch_station_data(self, station_id: str) -> dict[str, Any] | None:
        """Fetch data for a single charging station."""
        url = f"{API_BASE_URL}/chargestations/{station_id}"

        try:
            async with self.session.get(
                url, headers=API_HEADERS, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Fetched station data for %s", station_id)
                    return data
                else:
                    _LOGGER.error(
                        "Error fetching data for station %s: HTTP %s",
                        station_id,
                        response.status,
                    )
                    return None
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout fetching data for station %s", station_id)
            return None

    async def _update_occupancy_history(
        self, station_id: str, station_data: dict[str, Any]
    ) -> None:
        """Update occupancy history for a station."""
        if station_id not in self.occupancy_history:
            self.occupancy_history[station_id] = []

        now = dt_util.now()
        charge_points = station_data.get("chargePoints", [])

        occupancy_per_point = {}
        for cp in charge_points:
            evse_id = cp.get("evseId")
            status = cp.get("status")
            if evse_id:
                occupancy_per_point[evse_id] = {"status": status, "timestamp": now}

        # Keep only last 24 hours of data per point
        cutoff_time = now - timedelta(hours=24)
        history = self.occupancy_history[station_id]

        # Remove old entries
        history[:] = [
            entry
            for entry in history
            if entry.get("timestamp", now) > cutoff_time
        ]

        # Add new entry
        history.append(
            {
                "timestamp": now,
                "occupancy": occupancy_per_point,
                "hour": now.hour,
                "weekday": now.weekday(),
            }
        )

    def get_occupancy_by_weekday(self, station_id: str) -> dict[str, float]:
        """Get average occupancy by weekday."""
        history = self.occupancy_history.get(station_id, [])
        weekday_stats = {str(i): {"total": 0, "occupied": 0} for i in range(7)}

        for entry in history:
            weekday = entry.get("weekday", -1)
            if weekday >= 0:
                occupancy = entry.get("occupancy", {})
                for point_occupancy in occupancy.values():
                    weekday_stats[str(weekday)]["total"] += 1
                    if point_occupancy.get("status") == "Occupied":
                        weekday_stats[str(weekday)]["occupied"] += 1

        result = {}
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for day_num, stats in weekday_stats.items():
            total = stats["total"]
            occupied = stats["occupied"]
            percentage = (occupied / total * 100) if total > 0 else 0
            result[weekday_names[int(day_num)]] = round(percentage, 1)

        return result

    def get_occupancy_by_hour(self, station_id: str) -> dict[str, float]:
        """Get average occupancy by hour of day."""
        history = self.occupancy_history.get(station_id, [])
        hour_stats = {str(i): {"total": 0, "occupied": 0} for i in range(24)}

        for entry in history:
            hour = entry.get("hour", -1)
            if hour >= 0:
                occupancy = entry.get("occupancy", {})
                for point_occupancy in occupancy.values():
                    hour_stats[str(hour)]["total"] += 1
                    if point_occupancy.get("status") == "Occupied":
                        hour_stats[str(hour)]["occupied"] += 1

        result = {}
        for hour_num, stats in hour_stats.items():
            total = stats["total"]
            occupied = stats["occupied"]
            percentage = (occupied / total * 100) if total > 0 else 0
            result[f"{int(hour_num):02d}:00"] = round(percentage, 1)

        return result

    def get_station_location(self, station_id: str, point_data: dict) -> dict:
        """Extract location data from station point."""
        location = point_data.get("location", {})
        return {
            "latitude": location.get("latitude", 0),
            "longitude": location.get("longitude", 0),
            "address": location.get("address", "Unknown"),
        }
