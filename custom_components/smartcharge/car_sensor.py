"""Car sensor entities for SmartCharge integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

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
    CONF_ODOMETER_ENTITY,
    CONF_TARIFF_BASE_FEE,
    CONF_TARIFF_PRICE_PER_KWH,
    DOMAIN,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)

STORAGE_VERSION = 1


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
        self._energy_mix: dict[str, float] = {}
        self._energy_histogram: dict[str, float] = {}
        self._accum_energy: float = 0.0
        self._accum_co2: float = 0.0
        self._accum_cost_eur: float = 0.0
        self._total_km: float = 0.0

        # Private tracking state
        self._last_power: float = 0.0
        self._last_update = None
        self._last_odometer: float | None = None
        self._charging_session_station: str | None = None
        self._api_key_error_logged: bool = False

        # Persistent storage (loaded in async_added_to_hass)
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.car.{entry.entry_id}"
        )

        # Populated by sensor.py after all entities are created
        self._children: list[_CarChildSensor] = []

    async def async_added_to_hass(self) -> None:
        """Load persisted accumulator values when entity is added to HA."""
        await super().async_added_to_hass()
        stored = await self._store.async_load()
        if stored:
            self._accum_energy = stored.get("accum_energy", 0.0)
            self._accum_co2 = stored.get("accum_co2", 0.0)
            self._accum_cost_eur = stored.get("accum_cost_eur", 0.0)
            self._total_km = stored.get("total_km", 0.0)
            self._last_odometer = stored.get("last_odometer")
            _LOGGER.debug("Loaded persisted car accumulator data for %s", self.entry.entry_id)

    async def _save_accumulators(self) -> None:
        """Persist accumulator values to disk."""
        await self._store.async_save(
            {
                "accum_energy": self._accum_energy,
                "accum_co2": self._accum_co2,
                "accum_cost_eur": self._accum_cost_eur,
                "total_km": self._total_km,
                "last_odometer": self._last_odometer,
            }
        )

    def register_children(self, children: list[_CarChildSensor]) -> None:
        """Register child sensors to be refreshed after each update."""
        self._children = children

    def _find_nearby_station(
        self,
        car_lat: float,
        car_lon: float,
        gps_accuracy: float | None,
    ) -> tuple[str | None, float | None, float]:
        """Return (entry_id, price_ct_per_kwh, base_fee_ct) for the nearest
        station with a tariff within proximity threshold.
        Returns (None, None, 0.0) when none found."""
        # Safe-cast: gps_accuracy may arrive as a string from some integrations.
        try:
            threshold = (
                max(float(gps_accuracy), 50.0) if gps_accuracy is not None else 50.0
            )
        except (TypeError, ValueError):
            threshold = 50.0
        domain_data = self.hass.data.get(DOMAIN, {})
        for station_entry in self.hass.config_entries.async_entries(DOMAIN):
            if station_entry.data.get("entry_type") == "car":
                continue
            coordinator = domain_data.get(station_entry.entry_id)
            if coordinator is None or coordinator.data is None:
                continue
            station_lat = coordinator.data.get("lat")
            station_lon = coordinator.data.get("lon")
            if station_lat is None or station_lon is None:
                continue
            dist = geo_distance(car_lat, car_lon, station_lat, station_lon)
            if dist is None or dist > threshold:
                continue
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
            return station_entry.entry_id, tariff_price_f, tariff_base_f
        return None, None, 0.0

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
                self._last_odometer = current_odometer

        # --- electricityMap API ---
        co2_intensity: float | None = None
        energy_mix: dict[str, float] = {}
        if latitude is not None and longitude is not None:
            try:
                session = async_get_clientsession(self.hass)
                api_key = self.entry.options.get("electricitymap_api_key", "")
                headers = {"auth-token": api_key, "Accept": "application/json"}
                url = (
                    "https://api.electricitymap.org/v3/carbon-intensity/latest"
                    f"?lat={latitude}&lon={longitude}"
                )
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        co2_intensity = data.get("carbonIntensity")
                        self._api_key_error_logged = False
                        for src in data.get("generationMix", []):
                            energy_mix[src.get("productionType", "other")] = src.get(
                                "percent", 0
                            )
                    elif resp.status in (401, 403):
                        if not self._api_key_error_logged:
                            _LOGGER.warning(
                                "electricityMap returned HTTP %s — API key is invalid "
                                "or expired. Update it via Settings → Devices & Services "
                                "→ SmartCharge → Configure.",
                                resp.status,
                            )
                            self._api_key_error_logged = True
                        else:
                            _LOGGER.debug(
                                "electricityMap still returning HTTP %s (key not updated)",
                                resp.status,
                            )
                    else:
                        _LOGGER.warning("electricityMap returned HTTP %s", resp.status)
            except Exception as exc:
                _LOGGER.warning("Failed to fetch electricityMap data: %s", exc)
        else:
            _LOGGER.debug("No GPS location available, skipping electricityMap call")

        # --- Station proximity & billing session ---
        # Only open/close sessions when the power reading is valid; an unavailable
        # power sensor must not look like the car stopped charging.
        nearby_station_id: str | None = None
        tariff_price: float | None = None
        tariff_base: float = 0.0
        if latitude is not None and longitude is not None:
            nearby_station_id, tariff_price, tariff_base = self._find_nearby_station(
                latitude, longitude, gps_accuracy
            )

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
                for src, pct in energy_mix.items():
                    if pct >= 0:
                        self._energy_histogram[src] = (
                            self._energy_histogram.get(src, 0.0)
                            + delta_energy * pct / 100.0
                        )

        # Always advance the timestamp so the next interval is correctly sized.
        # Only advance _last_power when we have a valid reading so the trapezoid
        # uses the last known good value as its left endpoint on recovery.
        self._last_update = now
        if power_available:
            self._last_power = charging_power
        self._state = co2_intensity
        self._energy_mix = energy_mix

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
        return {
            "energy_mix": self._energy_mix,
            "energy_histogram": self._energy_histogram,
        }


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
