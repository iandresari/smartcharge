"""Data coordinator for EnBW Charging integration."""

from __future__ import annotations

import asyncio
import logging
import re
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
    API_FALLBACK_SUBSCRIPTION_KEY,
    API_HEADERS,
    API_MAP_URL,
    CONF_AUTO_API_KEY,
    CONF_CHARGING_STATIONS,
    CONF_MANUAL_API_KEY,
    CONF_STATION_ID,
    DEFAULT_AUTO_API_KEY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)

# Module-level cache shared across all coordinator instances
_cached_api_key: str | None = None


async def fetch_api_key(session: aiohttp.ClientSession) -> str:
    """Fetch the current API subscription key from the EnBW map page."""
    global _cached_api_key  # noqa: PLW0603

    try:
        async with session.get(
            API_MAP_URL,
            timeout=aiohttp.ClientTimeout(total=15),
            headers={"User-Agent": "Home Assistant / EnBW Charging Integration"},
        ) as response:
            if response.status != 200:
                _LOGGER.warning(
                    "Could not fetch EnBW map page (HTTP %s),"
                    " using cached/fallback key",
                    response.status,
                )
                return _cached_api_key or API_FALLBACK_SUBSCRIPTION_KEY

            html = await response.text()

        match = re.search(
            r'apimSubscriptionKey\s*[:\"=]+\s*["\']([a-f0-9]{32})["\']', html
        )
        if match:
            key = match.group(1)
            if key != _cached_api_key:
                _LOGGER.info("EnBW API subscription key updated")
            _cached_api_key = key
            return key

        _LOGGER.warning(
            "Could not extract API key from EnBW map page, using cached/fallback key"
        )
        return _cached_api_key or API_FALLBACK_SUBSCRIPTION_KEY

    except Exception as err:
        _LOGGER.warning("Error fetching API key: %s, using cached/fallback key", err)
        return _cached_api_key or API_FALLBACK_SUBSCRIPTION_KEY


def get_api_headers(api_key: str) -> dict[str, str]:
    """Build API headers with the given subscription key."""
    return {**API_HEADERS, "Ocp-Apim-Subscription-Key": api_key}


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
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )
        self.session = session
        self.entry = entry
        self.occupancy_history: dict[str, list[dict[str, Any]]] = {}
        self._api_key: str | None = _cached_api_key

    @property
    def _auto_api_key_enabled(self) -> bool:
        """Return whether automatic API key renewal is enabled."""
        return self.entry.options.get(CONF_AUTO_API_KEY, DEFAULT_AUTO_API_KEY)

    @property
    def _manual_api_key_value(self) -> str:
        """Return the manually configured API key, if any."""
        return self.entry.options.get(CONF_MANUAL_API_KEY, "")

    async def _resolve_api_key(self) -> str:
        """Resolve the API key based on configuration."""
        if not self._auto_api_key_enabled:
            manual_key = self._manual_api_key_value
            if manual_key:
                return manual_key
            _LOGGER.warning(
                "Auto API key is disabled but no manual key set, using fallback"
            )
            return API_FALLBACK_SUBSCRIPTION_KEY
        if not self._api_key:
            self._api_key = await fetch_api_key(self.session)
        return self._api_key

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
                        "Error fetching data for station %s: %s",
                        station_id,
                        err,
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
        api_key = await self._resolve_api_key()
        headers = get_api_headers(api_key)

        try:
            async with self.session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status in (401, 403) and self._auto_api_key_enabled:
                    _LOGGER.info(
                        "API key rejected (HTTP %s), refreshing key",
                        response.status,
                    )
                    self._api_key = await fetch_api_key(self.session)
                    headers = get_api_headers(self._api_key)
                    async with self.session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as retry_response:
                        if retry_response.status == 200:
                            data = await retry_response.json()
                            _LOGGER.debug(
                                "Fetched station data for %s (after key refresh)",
                                station_id,
                            )
                            return data
                        _LOGGER.error(
                            "Still failing after key refresh for station %s: HTTP %s",
                            station_id,
                            retry_response.status,
                        )
                        return None
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
                occupancy_per_point[evse_id] = {
                    "status": status,
                    "timestamp": now,
                }

        # Keep only last 24 hours of data per point
        cutoff_time = now - timedelta(hours=24)
        history = self.occupancy_history[station_id]

        # Remove old entries
        history[:] = [
            entry for entry in history if entry.get("timestamp", now) > cutoff_time
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
