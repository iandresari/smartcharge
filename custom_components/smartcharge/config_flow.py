"""Config flow for EnBW Charging integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import LocationSelector, LocationSelectorConfig

from .const import (
    API_BASE_URL,
    CONF_AUTO_API_KEY,
    CONF_CHARGING_STATIONS,
    CONF_MANUAL_API_KEY,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_AUTO_API_KEY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import fetch_api_key, get_api_headers

_LOGGER: logging.Logger = logging.getLogger(__name__)


class EnBWChargingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EnBW Charging."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self.station_data: dict[str, Any] | None = None
        self.selected_charge_points: list[str] = []
        self._nearby_stations: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step - choose to search map, browse, or enter ID."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "search":
                return await self.async_step_search_map()
            if action == "browse":
                return await self.async_step_browse_map()
            return await self.async_step_enter_station_id()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="search"): vol.In(
                        {
                            "search": "Search Nearby Stations (Recommended)",
                            "browse": "Browse EnBW Map & Enter Station ID",
                            "manual": "Enter Station ID Directly",
                        }
                    ),
                }
            ),
            description_placeholders={
                "map_url": (
                    "https://www.enbw.com/elektromobilitaet/produkte/"
                    "mobilityplus-app/ladestation-finden/map"
                )
            },
        )

    async def async_step_browse_map(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Direct user to EnBW map to find station."""
        if user_input is not None:
            return await self.async_step_enter_station_id()

        return self.async_show_form(
            step_id="browse_map",
            data_schema=vol.Schema({}),
            description_placeholders={
                "map_url": (
                    "https://www.enbw.com/elektromobilitaet/produkte/"
                    "mobilityplus-app/ladestation-finden/map"
                )
            },
        )

    async def async_step_search_map(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show a map for the user to pick a search location."""
        errors = {}

        if user_input is not None:
            loc = user_input.get("location", {})
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            radius_m = loc.get("radius", 5000)

            if lat is None or lon is None:
                errors["base"] = "no_location"
            else:
                try:
                    radius_deg = radius_m / 111_000
                    self._nearby_stations = await self._search_stations_area(
                        lat - radius_deg,
                        lat + radius_deg,
                        lon - radius_deg,
                        lon + radius_deg,
                    )
                    if self._nearby_stations:
                        return await self.async_step_select_station()
                    errors["base"] = "no_stations_found"
                except ConnectionError:
                    errors["base"] = "connection_error"
                except Exception as err:
                    _LOGGER.error("Error searching stations: %s", err)
                    errors["base"] = "unknown_error"

        default_location = {
            "latitude": self.hass.config.latitude,
            "longitude": self.hass.config.longitude,
            "radius": 5000,
        }

        return self.async_show_form(
            step_id="search_map",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "location", default=default_location
                    ): LocationSelector(
                        LocationSelectorConfig(radius=True, icon="mdi:ev-station")
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_select_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let user pick a station from the search results."""
        if user_input is not None:
            station_id = user_input.get("station")
            try:
                self.station_data = await self._fetch_station_details(station_id)
                return await self.async_step_select_charge_points()
            except ConnectionError as err:
                _LOGGER.error("Connection error: %s", err)
                return await self.async_step_search_map()
            except ValueError as err:
                _LOGGER.error("Invalid station: %s", err)
                return await self.async_step_search_map()

        options = {}
        station_details_lines = []
        for s in self._nearby_stations:
            sid = str(s.get("stationId", ""))
            name = s.get("name", "Unknown Station")
            addr = s.get("address", {})
            street = addr.get("street", "")
            city = addr.get("city", "")
            location_str = ", ".join(filter(None, [street, city]))
            label = f"{name} — {location_str}" if location_str else name
            options[sid] = label

            loc = s.get("location", {})
            lat = loc.get("latitude", "?")
            lon = loc.get("longitude", "?")
            detail = f"- **{name}** (ID: {sid})"
            if location_str:
                detail += f"\n  {location_str}"
            detail += f"\n  GPS: {lat}, {lon}"
            station_details_lines.append(detail)

        station_details = "\n".join(station_details_lines)

        return self.async_show_form(
            step_id="select_station",
            data_schema=vol.Schema(
                {
                    vol.Required("station"): vol.In(options),
                }
            ),
            description_placeholders={
                "station_count": str(len(self._nearby_stations)),
                "station_details": station_details,
            },
        )

    async def _search_stations_area(
        self,
        from_lat: float,
        to_lat: float,
        from_lon: float,
        to_lon: float,
    ) -> list[dict[str, Any]]:
        """Search for charging stations in a geographic area."""
        session = async_get_clientsession(self.hass)
        api_key = await fetch_api_key(session)
        headers = get_api_headers(api_key)

        url = (
            f"{API_BASE_URL}/chargestations"
            f"?fromLat={from_lat}&toLat={to_lat}"
            f"&fromLon={from_lon}&toLon={to_lon}"
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

            if isinstance(data, list):
                return data
            return []

        except asyncio.TimeoutError as err:
            raise ConnectionError("Search request timed out") from err

    async def async_step_enter_station_id(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle entering station ID."""
        errors = {}

        if user_input is not None:
            station_id = user_input.get(CONF_STATION_ID, "").strip()

            if not station_id:
                errors["base"] = "missing_station_id"
            else:
                try:
                    # Fetch and validate station
                    self.station_data = await self._fetch_station_details(station_id)
                    return await self.async_step_select_charge_points()

                except ConnectionError as err:
                    _LOGGER.error("Connection error: %s", err)
                    errors["base"] = "connection_error"
                except ValueError as err:
                    _LOGGER.error("Invalid station: %s", err)
                    errors["base"] = "invalid_station"
                except Exception as err:
                    _LOGGER.error("Unexpected error: %s", err)
                    errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="enter_station_id",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID): vol.All(str, vol.Length(min=1)),
                }
            ),
            errors=errors,
            description_placeholders={
                "map_url": (
                    "https://www.enbw.com/elektromobilitaet/produkte/"
                    "mobilityplus-app/ladestation-finden/map"
                )
            },
        )

    async def async_step_select_charge_points(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let user select which charge points to monitor."""
        if not self.station_data:
            return self.async_abort(reason="no_station_data")

        if user_input is not None:
            selected = user_input.get("charge_points", [])
            if not selected:
                return self.async_show_form(
                    step_id="select_charge_points",
                    data_schema=self._build_charge_points_schema(),
                    errors={"base": "no_charge_points_selected"},
                )

            self.selected_charge_points = selected
            return await self.async_step_configure_settings()

        return self.async_show_form(
            step_id="select_charge_points",
            data_schema=self._build_charge_points_schema(),
            description_placeholders={
                "station_name": self.station_data.get("name", "Unknown"),
                "charge_point_count": str(
                    len(self.station_data.get("charge_points", []))
                ),
            },
        )

    def _build_charge_points_schema(self) -> vol.Schema:
        """Build schema for selecting charge points."""
        if not self.station_data:
            return vol.Schema({})

        charge_points = self.station_data.get("charge_points", [])
        charge_point_options = {}

        for cp in charge_points:
            evse_id = cp.get("evse_id")
            name = cp.get("name", evse_id)
            connector = cp.get("connector_type", "Unknown")
            power = cp.get("power", "Unknown")

            display_text = f"{name} ({connector}, {power}kW)"
            charge_point_options[evse_id] = display_text

        return vol.Schema(
            {
                vol.Required("charge_points"): cv.multi_select(charge_point_options),
            }
        )

    async def async_step_configure_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure general settings like update interval."""
        if user_input is not None:
            update_interval = user_input.get(
                CONF_UPDATE_INTERVAL,
                DEFAULT_UPDATE_INTERVAL,
            )
            auto_api_key = user_input.get(CONF_AUTO_API_KEY, DEFAULT_AUTO_API_KEY)
            manual_api_key = user_input.get(CONF_MANUAL_API_KEY, "").strip()

            return self.async_create_entry(
                title=(f"EnBW - " f"{self.station_data.get(
                        'name', 'Charging Station'
                    )}"),
                data={
                    CONF_CHARGING_STATIONS: [
                        {
                            CONF_STATION_ID: self.station_data.get("station_id"),
                            CONF_STATION_NAME: self.station_data.get("name"),
                            "charge_points": [
                                cp
                                for cp in self.station_data.get("charge_points", [])
                                if cp.get("evse_id") in self.selected_charge_points
                            ],
                        }
                    ],
                    CONF_UPDATE_INTERVAL: update_interval,
                },
                options={
                    CONF_AUTO_API_KEY: auto_api_key,
                    CONF_MANUAL_API_KEY: manual_api_key,
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=60, max=3600),
                ),
                vol.Optional(
                    CONF_AUTO_API_KEY,
                    default=DEFAULT_AUTO_API_KEY,
                ): bool,
                vol.Optional(
                    CONF_MANUAL_API_KEY,
                    default="",
                ): str,
            }
        )

        return self.async_show_form(
            step_id="configure_settings",
            data_schema=schema,
            description_placeholders={
                "update_interval_description": (
                    "How often to fetch data" " (60-3600 seconds)"
                )
            },
        )

    async def _fetch_station_details(self, station_id: str) -> dict[str, Any]:
        """Fetch station data from EnBW API and extract charge points."""
        session = async_get_clientsession(self.hass)
        url = f"{API_BASE_URL}/chargestations/{station_id}"
        api_key = await fetch_api_key(session)
        headers = get_api_headers(api_key)

        try:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in (401, 403):
                    _LOGGER.info(
                        "API key rejected (HTTP %s), refreshing", response.status
                    )
                    api_key = await fetch_api_key(session)
                    headers = get_api_headers(api_key)
                    async with session.get(
                        url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                    ) as retry:
                        if retry.status == 404:
                            raise ValueError(
                                f"Station {station_id} not found. "
                                f"Please verify the station ID on the map."
                            )
                        if retry.status != 200:
                            raise ConnectionError(
                                f"API returned HTTP {retry.status}. "
                                f"Please try again in a moment."
                            )
                        data = await retry.json()
                elif response.status == 404:
                    raise ValueError(
                        f"Station {station_id} not found. "
                        f"Please verify the station ID on the map."
                    )
                elif response.status != 200:
                    raise ConnectionError(
                        f"API returned HTTP {response.status}. "
                        f"Please try again in a moment."
                    )
                else:
                    data = await response.json()

                if not data.get("chargePoints"):
                    raise ValueError("Station has no charge points")

                charge_points = []
                for cp in data.get("chargePoints", []):
                    charge_points.append(
                        {
                            "evse_id": cp.get("evseId"),
                            "name": cp.get("evse", {}).get("name", cp.get("evseId")),
                            "connector_type": cp.get("connectorType"),
                            "power": cp.get("powerKw"),
                            "status": cp.get("status"),
                            "location": cp.get("location", {}),
                        }
                    )

                return {
                    "station_id": station_id,
                    "name": data.get("name", f"Station {station_id}"),
                    "charge_points": charge_points,
                    "location": data.get("location", {}),
                }

        except asyncio.TimeoutError as err:
            raise ConnectionError("Request timed out. Please try again.") from err
        except (ConnectionError, ValueError):
            raise
        except Exception as err:
            _LOGGER.error("Error fetching station details: %s", err)
            raise


class EnBWChargingOptionsFlow(config_entries.OptionsFlow):
    """Options flow for EnBW Charging."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        update_interval = self.config_entry.data.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        auto_api_key = self.config_entry.options.get(
            CONF_AUTO_API_KEY, DEFAULT_AUTO_API_KEY
        )
        manual_api_key = self.config_entry.options.get(CONF_MANUAL_API_KEY, "")

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL, default=update_interval
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                    vol.Optional(CONF_AUTO_API_KEY, default=auto_api_key): bool,
                    vol.Optional(CONF_MANUAL_API_KEY, default=manual_api_key): str,
                }
            ),
        )

    async def async_step_add_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new charging station through options."""
        errors = {}

        if user_input is not None:
            station_id = user_input.get(CONF_STATION_ID, "").strip()

            if not station_id:
                errors["base"] = "missing_station_id"
            else:
                # Check for duplicates
                current_stations = self.config_entry.data.get(
                    CONF_CHARGING_STATIONS, []
                )
                if any(s.get(CONF_STATION_ID) == station_id for s in current_stations):
                    errors["base"] = "station_exists"
                else:
                    try:
                        station_data = await self._fetch_station_details(station_id)

                        current_stations.append(
                            {
                                CONF_STATION_ID: station_id,
                                CONF_STATION_NAME: station_data["name"],
                                "charge_points": station_data["charge_points"],
                            }
                        )

                        self.hass.config_entries.async_update_entry(
                            self.config_entry,
                            data={
                                **self.config_entry.data,
                                CONF_CHARGING_STATIONS: current_stations,
                            },
                        )
                        return self.async_abort(reason="station_added")

                    except Exception as err:
                        _LOGGER.error("Error adding station: %s", err)
                        errors["base"] = "connection_error"

        return self.async_show_form(
            step_id="add_station",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID): str,
                }
            ),
            errors=errors,
        )

    async def _fetch_station_details(self, station_id: str) -> dict[str, Any]:
        """Fetch station data from EnBW API."""
        session = async_get_clientsession(self.hass)
        url = f"{API_BASE_URL}/chargestations/{station_id}"
        api_key = await fetch_api_key(session)
        headers = get_api_headers(api_key)

        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status in (401, 403):
                api_key = await fetch_api_key(session)
                headers = get_api_headers(api_key)
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                ) as retry:
                    if retry.status != 200:
                        raise ConnectionError(
                            f"Station not found (HTTP {retry.status})"
                        )
                    data = await retry.json()
            elif response.status != 200:
                raise ConnectionError(f"Station not found (HTTP {response.status})")
            else:
                data = await response.json()
            if not data.get("chargePoints"):
                raise ValueError("No charge points found for station")

            charge_points = []
            for cp in data.get("chargePoints", []):
                charge_points.append(
                    {
                        "evse_id": cp.get("evseId"),
                        "name": cp.get("evse", {}).get("name", cp.get("evseId")),
                        "connector_type": cp.get("connectorType"),
                        "power": cp.get("powerKw"),
                    }
                )

            return {
                "station_id": station_id,
                "name": data.get("name", f"Station {station_id}"),
                "charge_points": charge_points,
            }


# Link options flow with config flow
EnBWChargingConfigFlow.async_get_options_flow = (
    lambda config_entry: EnBWChargingOptionsFlow(config_entry)
)
