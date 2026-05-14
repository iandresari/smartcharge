"""Car sensor entities for SmartCharge integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util
from homeassistant.util.location import distance as geo_distance

from .const import (
    CONF_AUTO_DISCOVERY,
    CONF_CAR_ENTRY_ID,
    CONF_CO2_ENTITY,
    CONF_ODOMETER_ENTITY,
    CONF_ODOMETER_SNAPSHOT,
    CONF_PRICE_ENTITY,
    CONF_TARIFF_BASE_FEE,
    CONF_TARIFF_PRICE_PER_KWH,
    DEFAULT_AUTO_DISCOVERY,
    DOMAIN,
    ENTRY_TYPE_TEMPORARY,
    ENTRY_TYPE_WALLBOX,
    STORAGE_VERSION,
)
from .coordinator import async_search_stations

_LOGGER: logging.Logger = logging.getLogger(__name__)


class CarChargingSensor(SensorEntity):
    """Primary car sensor: state = live CO2 intensity, attrs = energy mix."""

    _attr_should_poll = True
    _attr_has_entity_name = True
    _attr_name = "CO2 Intensity"
    _attr_native_unit_of_measurement = "gCO2/kWh"
    _attr_icon = "mdi:molecule-co2"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__()
        self.hass = hass
        self.entry = entry
        car_name = entry.data.get("car_name", "")
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=car_name,
            model="Electric Vehicle",
        )

        # Internal state — read by child sensors
        self._state: float | None = None
        self._accum_energy: float = 0.0
        self._accum_co2: float = 0.0
        self._accum_cost_eur: float = 0.0
        self._total_km: float = 0.0

        # Private tracking state
        self._last_power: float = 0.0
        self._last_update = None
        self._last_odometer: float | None = None
        self._charging_session_station: str | None = None
        self._discovery_triggered: bool = False

        # Persistent storage (loaded in async_added_to_hass)
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.car.{entry.entry_id}"
        )

        # Populated by sensor.py after all entities are created
        self._children: list[_CarChildSensor] = []

    async def async_added_to_hass(self) -> None:
        """Load persisted accumulator values when entity is added to HA."""
        await super().async_added_to_hass()
        try:
            stored = await self._store.async_load()
        except Exception as err:
            _LOGGER.warning(
                "Failed to load persisted accumulator data for %s: %s",
                self.entry.entry_id,
                err,
            )
            stored = None
        if stored:
            self._accum_energy = stored.get("accum_energy", 0.0)
            self._accum_co2 = stored.get("accum_co2", 0.0)
            self._accum_cost_eur = stored.get("accum_cost_eur", 0.0)
            self._total_km = stored.get("total_km", 0.0)
            self._last_odometer = stored.get("last_odometer")
            _LOGGER.debug(
                "Loaded persisted car accumulator data for %s",
                self.entry.entry_id,
            )

    async def _save_accumulators(self) -> None:
        """Persist accumulator values to disk."""
        try:
            await self._store.async_save(
                {
                    "accum_energy": self._accum_energy,
                    "accum_co2": self._accum_co2,
                    "accum_cost_eur": self._accum_cost_eur,
                    "total_km": self._total_km,
                    "last_odometer": self._last_odometer,
                }
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed to persist accumulator data for %s: %s",
                self.entry.entry_id,
                err,
            )

    def register_children(self, children: list[_CarChildSensor]) -> None:
        """Register child sensors to be refreshed after each update."""
        self._children = children

    def _find_nearby_station(
        self,
        car_lat: float,
        car_lon: float,
        gps_accuracy: float | None,
    ) -> tuple[str | None, float | None, float, str | None]:
        """Return (entry_id, price_ct_per_kwh, base_fee_ct, co2_entity_id)
        for the nearest station within the proximity threshold.
        Returns (None, None, 0.0, None) when none found."""
        try:
            threshold = (
                max(float(gps_accuracy), 50.0) if gps_accuracy is not None else 50.0
            )
        except (TypeError, ValueError):
            threshold = 50.0

        domain_data = self.hass.data.get(DOMAIN, {})
        for station_entry in self.hass.config_entries.async_entries(DOMAIN):
            entry_type = station_entry.data.get("entry_type")
            if entry_type == "car":
                continue

            entry_value = domain_data.get(station_entry.entry_id)
            if entry_value is None:
                continue

            if entry_type in (ENTRY_TYPE_TEMPORARY, ENTRY_TYPE_WALLBOX):
                # Plain dict stored by __init__.py for lightweight entries.
                station_lat = entry_value.get("lat")
                station_lon = entry_value.get("lon")
            else:
                # Coordinator object for regular EnBW stations.
                if not hasattr(entry_value, "data") or entry_value.data is None:
                    continue
                station_lat = entry_value.data.get("lat")
                station_lon = entry_value.data.get("lon")

            if station_lat is None or station_lon is None:
                continue
            dist = geo_distance(car_lat, car_lon, station_lat, station_lon)
            if dist is None or dist > threshold:
                continue

            if entry_type == ENTRY_TYPE_WALLBOX:
                price_entity_id = station_entry.options.get(CONF_PRICE_ENTITY)
                co2_entity_id = station_entry.options.get(CONF_CO2_ENTITY)
                if price_entity_id is None:
                    continue
                price_state = self.hass.states.get(price_entity_id)
                if price_state is None or price_state.state in (
                    "unavailable",
                    "unknown",
                ):
                    _LOGGER.debug(
                        "Wallbox price entity %s unavailable", price_entity_id
                    )
                    continue
                try:
                    tariff_price_f = float(price_state.state)
                except (TypeError, ValueError):
                    _LOGGER.warning(
                        "Could not parse wallbox price entity %s", price_entity_id
                    )
                    continue
                return station_entry.entry_id, tariff_price_f, 0.0, co2_entity_id

            if entry_type == ENTRY_TYPE_TEMPORARY:
                tariff_price = station_entry.options.get(CONF_TARIFF_PRICE_PER_KWH)
                if tariff_price is None:
                    continue
                try:
                    tariff_price_f = float(tariff_price)
                    tariff_base_f = float(
                        station_entry.options.get(CONF_TARIFF_BASE_FEE, 0) or 0
                    )
                except (TypeError, ValueError):
                    _LOGGER.warning(
                        "Invalid tariff config for temporary station %s, skipping",
                        station_entry.entry_id,
                    )
                    continue
                return station_entry.entry_id, tariff_price_f, tariff_base_f, None

            # Regular EnBW station
            tariff_price = station_entry.options.get(CONF_TARIFF_PRICE_PER_KWH)
            if tariff_price is None:
                continue
            try:
                tariff_price_f = float(tariff_price)
                tariff_base_f = float(
                    station_entry.options.get(CONF_TARIFF_BASE_FEE, 0) or 0
                )
            except (TypeError, ValueError):
                _LOGGER.warning(
                    "Invalid tariff config for station %s, skipping",
                    station_entry.entry_id,
                )
                continue
            return station_entry.entry_id, tariff_price_f, tariff_base_f, None

        return None, None, 0.0, None

    async def _cleanup_temporary_stations(self, current_odometer: float) -> None:
        """Remove temporary station entries for THIS car whose snapshot was exceeded."""
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("entry_type") != ENTRY_TYPE_TEMPORARY:
                continue
            # Only manage stations that belong to this car entry.
            if entry.data.get(CONF_CAR_ENTRY_ID) != self.entry.entry_id:
                continue
            snapshot = entry.data.get(CONF_ODOMETER_SNAPSHOT, 0.0)
            if snapshot < current_odometer:
                _LOGGER.info(
                    "Removing temporary station %s "
                    "(odometer snapshot %.1f km < current %.1f km)",
                    entry.entry_id,
                    snapshot,
                    current_odometer,
                )
                self.hass.async_create_task(
                    self.hass.config_entries.async_remove(entry.entry_id)
                )

    async def _trigger_station_discovery(
        self,
        lat: float,
        lon: float,
        gps_accuracy: float | None,  # noqa: ARG002  (reserved for future radius tuning)
    ) -> None:
        """Search for a nearby EnBW station and fire an integration_discovery flow."""
        # Avoid starting a second flow when one is already waiting for the user.
        for progress in self.hass.config_entries.flow.async_progress():
            if (
                progress.get("handler") == DOMAIN
                and progress.get("context", {}).get("source") == "integration_discovery"
            ):
                _LOGGER.debug(
                    "Auto-discovery flow already in progress, skipping new trigger"
                )
                return

        session = async_get_clientsession(self.hass)
        stations: list[dict] = []
        for radius_m in (50, 100, 200):
            try:
                stations = await async_search_stations(session, lat, lon, radius_m)
                if stations:
                    break
            except Exception as err:
                _LOGGER.debug("Auto-discovery search at %d m failed: %s", radius_m, err)
                return

        if not stations:
            _LOGGER.debug("Auto-discovery: no stations found within 200 m")
            return

        _LOGGER.info(
            "Auto-discovery: found %d station(s) near car, opening config flow",
            len(stations),
        )
        self.hass.async_create_task(
            self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "integration_discovery"},
                data={"stations": stations, "car_entry_id": self.entry.entry_id},
            )
        )

    async def async_update(self) -> None:
        """Fetch power, location, electricity map data; integrate accumulators."""
        # --- Charging power ---
        # Track availability separately so that a temporarily unavailable entity
        # does not look like 0 W, which would prematurely end a billing session
        # and corrupt the trapezoidal integration on recovery.
        power_entity = self.entry.data.get("charging_power_entity")
        power_state = self.hass.states.get(power_entity)
        power_available = False
        charging_power = 0.0
        if power_state is None:
            _LOGGER.debug("Charging power entity %s not found", power_entity)
        elif power_state.state in ("unavailable", "unknown"):
            _LOGGER.debug(
                "Charging power entity %s is %s, skipping integration",
                power_entity,
                power_state.state,
            )
        else:
            try:
                # Clamp to zero: negative values (e.g. reversed CT clamp /
                # V2G export) must not corrupt the trapezoid or billing logic.
                charging_power = max(0.0, float(power_state.state))
                power_available = True
            except (TypeError, ValueError):
                _LOGGER.debug(
                    "Could not parse charging power state: %s", power_state.state
                )

        # --- Location & GPS accuracy ---
        # Explicitly reject unavailable/unknown tracker states so stale GPS
        # attributes are never used for proximity billing or CO2 lookups.
        tracker_entity = self.entry.data.get("device_tracker")
        tracker_state = self.hass.states.get(tracker_entity)
        latitude: float | None = None
        longitude: float | None = None
        gps_accuracy: float | None = None
        if tracker_state is None:
            _LOGGER.debug("Device tracker entity %s not found", tracker_entity)
        elif tracker_state.state in ("unavailable", "unknown"):
            _LOGGER.debug(
                "Device tracker %s is %s", tracker_entity, tracker_state.state
            )
        else:
            latitude = tracker_state.attributes.get("latitude")
            longitude = tracker_state.attributes.get("longitude")
            # Use `is not None` (not truthiness) so that a reported value of
            # 0 (perfect accuracy) is not discarded in favour of `accuracy`.
            _raw_acc = tracker_state.attributes.get("gps_accuracy")
            gps_accuracy = (
                _raw_acc
                if _raw_acc is not None
                else tracker_state.attributes.get("accuracy")
            )

        # --- Odometer ---
        odometer_entity = self.entry.data.get(CONF_ODOMETER_ENTITY)
        if odometer_entity:
            odo_state = self.hass.states.get(odometer_entity)
            current_odometer: float | None = None
            if odo_state is not None and odo_state.state not in (
                "unavailable",
                "unknown",
            ):
                try:
                    current_odometer = float(odo_state.state)
                except (TypeError, ValueError):
                    _LOGGER.debug("Could not parse odometer state: %s", odo_state.state)
            if current_odometer is not None:
                if (
                    self._last_odometer is not None
                    and current_odometer > self._last_odometer
                ):
                    self._total_km += current_odometer - self._last_odometer
                    await self._cleanup_temporary_stations(current_odometer)
                self._last_odometer = current_odometer

        # --- Station proximity (resolved before CO2 to enable wallbox override) ---
        # Only open/close sessions when the power reading is valid; an unavailable
        # power sensor must not look like the car stopped charging.
        nearby_station_id: str | None = None
        tariff_price: float | None = None
        tariff_base: float = 0.0
        co2_entity_id: str | None = None
        if latitude is not None and longitude is not None:
            nearby_station_id, tariff_price, tariff_base, co2_entity_id = (
                self._find_nearby_station(latitude, longitude, gps_accuracy)
            )

        # --- CO2 intensity source ---
        # Priority: nearby wallbox entity → car's configured CO2 entity.
        co2_intensity: float | None = None
        co2_source = (
            co2_entity_id
            if co2_entity_id is not None and nearby_station_id is not None
            else self.entry.options.get(CONF_CO2_ENTITY) or None
        )
        if co2_source is not None:
            co2_state = self.hass.states.get(co2_source)
            if co2_state is not None and co2_state.state not in (
                "unavailable",
                "unknown",
            ):
                try:
                    co2_intensity = float(co2_state.state)
                except (TypeError, ValueError):
                    _LOGGER.debug(
                        "Could not parse CO2 entity state: %s", co2_state.state
                    )
            else:
                _LOGGER.debug("CO2 entity %s is unavailable", co2_source)

        # --- Billing session management ---
        if power_available:
            if nearby_station_id and charging_power > 0:
                if self._charging_session_station != nearby_station_id:
                    self._charging_session_station = nearby_station_id
                    self._accum_cost_eur += tariff_base / 100.0
                    _LOGGER.debug(
                        "Charging session started at station %s (base fee %.2f ct)",
                        nearby_station_id,
                        tariff_base,
                    )
            elif self._charging_session_station is not None and (
                charging_power == 0
                # Only close on proximity if GPS is actually valid; a temporary
                # GPS dropout must not look like the car left the station and
                # cause a duplicate base fee on the next reconnect.
                or (
                    latitude is not None
                    and longitude is not None
                    and nearby_station_id is None
                )
            ):
                _LOGGER.debug(
                    "Charging session ended at station %s",
                    self._charging_session_station,
                )
                self._charging_session_station = None
                self._discovery_triggered = False

        # --- Auto-discovery ---
        # When charging but no known station is nearby and no discovery has been
        # triggered for this session yet, search the EnBW API and open a
        # config-flow notification for the user.
        auto_discovery = self.entry.options.get(
            CONF_AUTO_DISCOVERY, DEFAULT_AUTO_DISCOVERY
        )
        if (
            auto_discovery
            and power_available
            and charging_power > 0
            and nearby_station_id is None
            and latitude is not None
            and longitude is not None
            and not self._discovery_triggered
        ):
            await self._trigger_station_discovery(latitude, longitude, gps_accuracy)
            self._discovery_triggered = True

        # --- Integrate energy, CO2, cost ---
        # Energy and cost accumulate whenever the power reading is valid so they
        # are not disrupted by CO2 API outages.  CO2 and the energy histogram
        # additionally require a live intensity value and are skipped otherwise.
        now = dt_util.utcnow()
        if power_available and self._last_update is not None:
            dt_hours = (now - self._last_update).total_seconds() / 3600.0
            avg_power = max((charging_power + self._last_power) / 2.0, 0.0)
            delta_energy = avg_power * dt_hours  # kWh (power entity must be in kW)
            self._accum_energy += delta_energy
            if self._charging_session_station and tariff_price is not None:
                self._accum_cost_eur += delta_energy * tariff_price / 100.0
            # Guard against malformed API responses (negative sentinel values).
            if co2_intensity is not None and co2_intensity >= 0:
                self._accum_co2 += delta_energy * co2_intensity

        # Always advance the timestamp so the next interval is correctly sized.
        # Only advance _last_power when we have a valid reading so the trapezoid
        # uses the last known good value as its left endpoint on recovery.
        self._last_update = now
        if power_available:
            self._last_power = charging_power
        self._state = co2_intensity

        # Persist accumulators so they survive HA restarts
        await self._save_accumulators()

        # Notify child sensors so they update in the same poll cycle
        for child in self._children:
            if child.hass is not None:
                child.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {}


# ---------------------------------------------------------------------------
# Child sensor base class
# ---------------------------------------------------------------------------


class _CarChildSensor(SensorEntity):
    """Base class for car child sensors that read from CarChargingSensor."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _name_suffix: str = ""
    _uid_suffix: str = ""

    def __init__(self, main: CarChargingSensor, entry: ConfigEntry) -> None:
        super().__init__()
        self._main = main
        self._attr_name = self._name_suffix
        self._attr_unique_id = f"{entry.entry_id}_{self._uid_suffix}"
        self._attr_device_info = main._attr_device_info


# ---------------------------------------------------------------------------
# Concrete child sensors
# ---------------------------------------------------------------------------


class CarAccumEnergySensor(_CarChildSensor):
    """Accumulated energy charged (kWh)."""

    _name_suffix = "Accumulated Energy"
    _uid_suffix = "energy"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:ev-station"

    @property
    def native_value(self) -> StateType:
        return round(self._main._accum_energy, 3)


class CarAccumCO2Sensor(_CarChildSensor):
    """Accumulated CO2 produced during charging (gCO2)."""

    _name_suffix = "Accumulated CO2"
    _uid_suffix = "co2_accum"
    _attr_native_unit_of_measurement = "gCO2"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:smog"

    @property
    def native_value(self) -> StateType:
        return round(self._main._accum_co2, 1)


class CarAccumCostSensor(_CarChildSensor):
    """Accumulated charging cost in EUR."""

    _name_suffix = "Accumulated Cost"
    _uid_suffix = "cost"
    _attr_native_unit_of_measurement = "EUR"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:currency-eur"

    @property
    def native_value(self) -> StateType:
        return round(self._main._accum_cost_eur, 2)


class CarCO2PerKmSensor(_CarChildSensor):
    """Average CO2 per km driven (gCO2/km)."""

    _name_suffix = "CO2 per km"
    _uid_suffix = "co2_per_km"
    _attr_native_unit_of_measurement = "gCO2/km"
    _attr_icon = "mdi:leaf"

    @property
    def native_value(self) -> StateType:
        if self._main._total_km <= 0:
            return None
        return round(self._main._accum_co2 / self._main._total_km, 1)


class CarCostPerKmSensor(_CarChildSensor):
    """Average charging cost per km driven (EUR/km)."""

    _name_suffix = "Cost per km"
    _uid_suffix = "cost_per_km"
    _attr_native_unit_of_measurement = "EUR/km"
    _attr_icon = "mdi:cash-marker"

    @property
    def native_value(self) -> StateType:
        if self._main._total_km <= 0:
            return None
        return round(self._main._accum_cost_eur / self._main._total_km, 4)
