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
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    LocationSelector,
    LocationSelectorConfig,
)

from .const import (
    API_BASE_URL,
    CONF_AUTO_API_KEY,
    CONF_MANUAL_API_KEY,
    CONF_ODOMETER_ENTITY,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    CONF_UPDATE_INTERVAL,
    CONF_STATIC_FRIENDLY_NAME,
    CONF_TARIFF_PRICE_PER_KWH,
    CONF_TARIFF_BASE_FEE,
    DEFAULT_AUTO_API_KEY,
    DEFAULT_TARIFF_BASE_FEE,
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
        self._nearby_stations: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Initial step: choose to add a Car or Charging Station."""
        if user_input is not None:
            selection = user_input.get("entry_type")
            if selection == "car":
                return await self.async_step_car()
            elif selection == "station":
                return await self.async_step_station()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("entry_type"): vol.In(
                        {
                            "car": "Car (track charging by GPS)",
                            "station": "Charging Station (EnBW or manual)",
                        }
                    )
                }
            ),
            description_placeholders={},
        )

    async def async_step_car(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Config flow for adding a car (GPS-based tracking)."""
        errors = {}
        if user_input is not None:
            car_name = user_input.get("car_name", "").strip()
            device_tracker = user_input.get("device_tracker", "").strip()
            charging_power_entity = user_input.get("charging_power_entity", "").strip()
            electricitymap_api_key = user_input.get(
                "electricitymap_api_key", ""
            ).strip()
            if (
                not car_name
                or not device_tracker
                or not charging_power_entity
                or not electricitymap_api_key
            ):
                errors["base"] = "missing_fields"
            else:
                odometer_entity = user_input.get(CONF_ODOMETER_ENTITY) or None
                # Save config entry for car, store API key in options
                return self.async_create_entry(
                    title=f"Car: {car_name}",
                    data={
                        "entry_type": "car",
                        "car_name": car_name,
                        "device_tracker": device_tracker,
                        "charging_power_entity": charging_power_entity,
                        CONF_ODOMETER_ENTITY: odometer_entity,
                    },
                    options={
                        "electricitymap_api_key": electricitymap_api_key,
                    },
                )
        return self.async_show_form(
            step_id="car",
            data_schema=vol.Schema(
                {
                    vol.Required("car_name"): str,
                    vol.Required("device_tracker"): EntitySelector(
                        EntitySelectorConfig(domain="device_tracker")
                    ),
                    vol.Required("charging_power_entity"): EntitySelector(
                        EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_ODOMETER_ENTITY): EntitySelector(
                        EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required("electricitymap_api_key"): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "api_key_help": (
                    "Enter your electricityMap API key. "
                    "Get one at https://electricitymaps.com/"
                )
            },
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Config flow for adding a charging station (existing logic)."""
        # Reuse the old user step logic for stations
        if user_input is not None:
            action = user_input.get("action")
            if action == "search":
                return await self.async_step_search_map()
            if action == "browse":
                return await self.async_step_browse_map()
            return await self.async_step_enter_station_id()

        return self.async_show_form(
            step_id="station",
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
                return await self.async_step_configure_settings()
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
            if not sid or sid == "None":
                continue  # Skip grouped results without station ID
            name = s.get(
                "stationSummary",
                s.get("shortAddress", f"Station {sid}"),
            )
            short_addr = s.get("shortAddress", "")
            label = f"{name} — {short_addr}" if short_addr else name
            options[sid] = label

            lat = s.get("lat", "?")
            lon = s.get("lon", "?")
            detail = f"- **{name}** (ID: {sid})"
            if short_addr and short_addr != name:
                detail += f"\n  {short_addr}"
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
                    return await self.async_step_configure_settings()

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

    async def async_step_configure_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """
        Configure general settings like update interval and static friendly name.
        """
        # Compute default static name: extract code after 'DE*' from first evse_id,
        # fallback to 'EVSE'
        charge_points = (
            self.station_data.get("charge_points", []) if self.station_data else []
        )
        first_evse = (
            charge_points[0]["evse_id"]
            if charge_points and charge_points[0].get("evse_id")
            else ""
        )
        code = "EVSE"
        if first_evse and first_evse.startswith("DE*"):
            parts = first_evse.split("*")
            if len(parts) > 1:
                code = parts[1]
        default_static = f"{code}_station_{self.station_data.get('station_id', '')}"

        if user_input is not None:
            update_interval = user_input.get(
                CONF_UPDATE_INTERVAL,
                DEFAULT_UPDATE_INTERVAL,
            )
            auto_api_key = user_input.get(CONF_AUTO_API_KEY, DEFAULT_AUTO_API_KEY)
            manual_api_key = user_input.get(CONF_MANUAL_API_KEY, "").strip()
            static_friendly_name = (
                user_input.get(CONF_STATIC_FRIENDLY_NAME, default_static).strip()
                or default_static
            )

            tariff_price = user_input.get(CONF_TARIFF_PRICE_PER_KWH)
            tariff_base = user_input.get(CONF_TARIFF_BASE_FEE, DEFAULT_TARIFF_BASE_FEE)

            return self.async_create_entry(
                title=static_friendly_name,
                data={
                    CONF_STATION_ID: self.station_data.get("station_id"),
                    CONF_STATION_NAME: self.station_data.get("name"),
                    CONF_UPDATE_INTERVAL: update_interval,
                    CONF_STATIC_FRIENDLY_NAME: static_friendly_name,
                },
                options={
                    CONF_AUTO_API_KEY: auto_api_key,
                    CONF_MANUAL_API_KEY: manual_api_key,
                    CONF_TARIFF_PRICE_PER_KWH: tariff_price,
                    CONF_TARIFF_BASE_FEE: tariff_base,
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
                vol.Optional(
                    CONF_STATIC_FRIENDLY_NAME,
                    default=default_static,
                ): str,
                vol.Required(
                    CONF_TARIFF_PRICE_PER_KWH,
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=0),
                ),
                vol.Optional(
                    CONF_TARIFF_BASE_FEE,
                    default=DEFAULT_TARIFF_BASE_FEE,
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=0),
                ),
            }
        )

        return self.async_show_form(
            step_id="configure_settings",
            data_schema=schema,
            description_placeholders={
                "update_interval_description": (
                    "How often to fetch data (60-3600 seconds)"
                ),
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
                        "API key rejected (HTTP %s), refreshing",
                        response.status,
                    )
                    api_key = await fetch_api_key(session)
                    headers = get_api_headers(api_key)
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
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
                    connectors = cp.get("connectors", [])
                    connector = connectors[0] if connectors else {}
                    charge_points.append(
                        {
                            "evse_id": cp.get("evseId"),
                            "name": cp.get("evseId"),
                            "connector_type": connector.get("plugTypeName", "Unknown"),
                            "power": connector.get("maxPowerInKw"),
                            "status": cp.get("status"),
                        }
                    )

                station_name = data.get(
                    "stationSummary",
                    data.get("shortAddress", f"Station {station_id}"),
                )

                return {
                    "station_id": station_id,
                    "name": station_name,
                    "charge_points": charge_points,
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
        """Handle options — branches on entry type."""
        if self.config_entry.data.get("entry_type") == "car":
            if user_input is not None:
                return self.async_create_entry(title="", data=user_input)
            current_key = self.config_entry.options.get("electricitymap_api_key", "")
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            "electricitymap_api_key", default=current_key
                        ): str,
                    }
                ),
            )

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        update_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL
        ) or self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        auto_api_key = self.config_entry.options.get(
            CONF_AUTO_API_KEY, DEFAULT_AUTO_API_KEY
        )
        manual_api_key = self.config_entry.options.get(CONF_MANUAL_API_KEY, "")
        tariff_price = self.config_entry.options.get(CONF_TARIFF_PRICE_PER_KWH, 0.0)
        tariff_base = self.config_entry.options.get(
            CONF_TARIFF_BASE_FEE, DEFAULT_TARIFF_BASE_FEE
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL, default=update_interval
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                    vol.Optional(CONF_AUTO_API_KEY, default=auto_api_key): bool,
                    vol.Optional(CONF_MANUAL_API_KEY, default=manual_api_key): str,
                    vol.Required(
                        CONF_TARIFF_PRICE_PER_KWH, default=tariff_price
                    ): vol.All(vol.Coerce(float), vol.Range(min=0)),
                    vol.Optional(CONF_TARIFF_BASE_FEE, default=tariff_base): vol.All(
                        vol.Coerce(float), vol.Range(min=0)
                    ),
                }
            ),
        )


# Link options flow with config flow
EnBWChargingConfigFlow.async_get_options_flow = (
    lambda config_entry: EnBWChargingOptionsFlow(config_entry)
)
