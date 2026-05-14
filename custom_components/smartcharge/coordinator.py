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
from homeassistant.helpers.storage import Store
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
    CONF_MANUAL_API_KEY,
    CONF_STATION_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_AUTO_API_KEY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    STORAGE_VERSION,
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
            (
                "Could not extract API key from EnBW map page,"
                " using cached/fallback key"
            )
        )
        return _cached_api_key or API_FALLBACK_SUBSCRIPTION_KEY

    except Exception as err:
        _LOGGER.warning("Error fetching API key: %s, using cached/fallback key", err)
        return _cached_api_key or API_FALLBACK_SUBSCRIPTION_KEY


def get_api_headers(api_key: str) -> dict[str, str]:
    """Build API headers with the given subscription key."""
    return {**API_HEADERS, "Ocp-Apim-Subscription-Key": api_key}


async def async_search_stations(
    session: aiohttp.ClientSession,
    lat: float,
    lon: float,
    radius_m: float,
) -> list[dict]:
    """Search for EnBW charging stations within *radius_m* metres of lat/lon.

    Tries the requested radius first.  If the API returns no results the
    caller is responsible for retrying with a larger radius.
    Raises ConnectionError on network/API failures.
    """
    api_key = await fetch_api_key(session)
    headers = get_api_headers(api_key)

    radius_deg = radius_m / 111_000.0
    url = (
        f"{API_BASE_URL}/chargestations"
        f"?fromLat={lat - radius_deg}&toLat={lat + radius_deg}"
        f"&fromLon={lon - radius_deg}&toLon={lon + radius_deg}"
        f"&grouping=false"
    )

    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
            if response.status in (401, 403):
                api_key = await fetch_api_key(session)
                headers = get_api_headers(api_key)
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as retry:
                    if retry.status != 200:
                        raise ConnectionError(f"API returned HTTP {retry.status}")
                    data = await retry.json()
            elif response.status != 200:
                raise ConnectionError(f"API returned HTTP {response.status}")
            else:
                data = await response.json()

        return data if isinstance(data, list) else []

    except asyncio.TimeoutError as err:
        raise ConnectionError("Station search request timed out") from err


def _empty_hourly_stats() -> dict[str, dict[str, int]]:
    """Return zeroed hourly statistics buckets (0-23)."""
    return {str(h): {"total": 0, "occupied": 0} for h in range(24)}


def _empty_weekday_stats() -> dict[str, dict[str, int]]:
    """Return zeroed weekday statistics buckets (0-6)."""
    return {str(d): {"total": 0, "occupied": 0} for d in range(7)}


class EnBWChargingCoordinator(DataUpdateCoordinator):
    """Coordinator for EnBW Charging data."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        entry: ConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        interval = int(
            entry.options.get(CONF_UPDATE_INTERVAL)
            or entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.session = session
        self.entry = entry
        self._api_key: str | None = _cached_api_key

        # Persistent statistics storage
        station_id = entry.data.get(CONF_STATION_ID, "unknown")
        self._store: Store = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.statistics.{station_id}",
        )
        self._hourly_stats: dict[str, dict[str, int]] = _empty_hourly_stats()
        self._weekday_stats: dict[str, dict[str, int]] = _empty_weekday_stats()
        self._stats_loaded = False

    async def _load_statistics(self) -> None:
        """Load accumulated statistics from persistent storage."""
        if self._stats_loaded:
            return

        stored = await self._store.async_load()
        if stored:
            self._hourly_stats = stored.get("hourly", _empty_hourly_stats())
            self._weekday_stats = stored.get("weekday", _empty_weekday_stats())
            _LOGGER.debug("Loaded persistent occupancy statistics")
        self._stats_loaded = True

    async def _save_statistics(self) -> None:
        """Persist accumulated statistics to disk."""
        await self._store.async_save(
            {
                "hourly": self._hourly_stats,
                "weekday": self._weekday_stats,
            }
        )

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
                ("Auto API key is disabled but no manual key set," " using fallback")
            )
            return API_FALLBACK_SUBSCRIPTION_KEY
        if not self._api_key:
            self._api_key = await fetch_api_key(self.session)
        return self._api_key

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from EnBW API."""
        try:
            await self._load_statistics()

            station_id = self.entry.data.get(CONF_STATION_ID)

            if not station_id:
                _LOGGER.debug("No station ID configured")
                return {}

            try:
                data = await self._fetch_station_data(station_id)
                if data:
                    await self._record_occupancy(data)
                    return data
            except Exception as err:
                _LOGGER.error(
                    "Error fetching data for station %s: %s",
                    station_id,
                    err,
                )

            return self.data or {}

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
                                ("Fetched station data for %s" " (after key refresh)"),
                                station_id,
                            )
                            return data
                        _LOGGER.error(
                            "Still failing after key refresh"
                            " for station %s: HTTP %s",
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

    async def _record_occupancy(self, station_data: dict[str, Any]) -> None:
        """Record occupancy sample into persistent histogram buckets."""
        now = dt_util.now()
        hour_key = str(now.hour)
        weekday_key = str(now.weekday())

        charge_points = station_data.get("chargePoints", [])
        if not charge_points:
            return

        for cp in charge_points:
            status = cp.get("status")
            if not status:
                continue

            # Hourly bucket
            self._hourly_stats[hour_key]["total"] += 1
            if status == "OCCUPIED":
                self._hourly_stats[hour_key]["occupied"] += 1

            # Weekday bucket
            self._weekday_stats[weekday_key]["total"] += 1
            if status == "OCCUPIED":
                self._weekday_stats[weekday_key]["occupied"] += 1

        await self._save_statistics()

    def get_occupancy_by_weekday(self) -> dict[str, float]:
        """Get accumulated average occupancy % by weekday."""
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        result = {}
        for day_num in range(7):
            stats = self._weekday_stats.get(str(day_num), {"total": 0, "occupied": 0})
            total = stats["total"]
            occupied = stats["occupied"]
            pct = (occupied / total * 100) if total > 0 else 0.0
            result[weekday_names[day_num]] = round(pct, 1)
        return result

    def get_occupancy_by_hour(self) -> dict[str, float]:
        """Get accumulated average occupancy % by hour of day."""
        result = {}
        for hour in range(24):
            stats = self._hourly_stats.get(str(hour), {"total": 0, "occupied": 0})
            total = stats["total"]
            occupied = stats["occupied"]
            pct = (occupied / total * 100) if total > 0 else 0.0
            result[f"{hour:02d}:00"] = round(pct, 1)
        return result
