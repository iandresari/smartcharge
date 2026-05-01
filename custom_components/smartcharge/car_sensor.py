"""Car sensor entity for SmartCharge integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

_LOGGER: logging.Logger = logging.getLogger(__name__)


class CarChargingSensor(SensorEntity):
    """Sensor for car charging, CO2, and energy mix."""

    _attr_should_poll = True
    _attr_native_unit_of_measurement = "gCO2/kWh"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__()
        self.hass = hass
        self.entry = entry
        self._attr_name = f"Car Charging CO2 ({entry.data.get('car_name')})"
        self._attr_unique_id = entry.entry_id
        self._state = None
        self._attrs: dict[str, Any] = {}
        self._last_power = 0.0
        self._last_update = None
        self._accum_energy = 0.0
        self._accum_co2 = 0.0
        self._energy_histogram = {}

    async def async_update(self) -> None:
        """Fetch latest charging power, location, and electricity map data."""
        # Get current charging power
        power_entity = self.entry.data.get("charging_power_entity")
        power_state = self.hass.states.get(power_entity)
        try:
            charging_power = float(power_state.state)
        except (TypeError, ValueError, AttributeError):
            charging_power = 0.0

        # Get current location
        tracker_entity = self.entry.data.get("device_tracker")
        tracker_state = self.hass.states.get(tracker_entity)
        latitude = tracker_state.attributes.get("latitude") if tracker_state else None
        longitude = tracker_state.attributes.get("longitude") if tracker_state else None

        # Fetch electricityMap data (real API call)
        co2_intensity = None
        energy_mix = {}
        if latitude is not None and longitude is not None:
            try:
                session = async_get_clientsession(self.hass)
                electricitymap_api_key = self.entry.options.get(
                    "electricitymap_api_key", "YOUR_API_KEY"
                )
                headers = {
                    "auth-token": electricitymap_api_key,
                    "Accept": "application/json",
                }
                url = (
                    "https://api.electricitymap.org/v3/carbon-intensity/latest"
                    f"?lat={latitude}&lon={longitude}"
                )
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        co2_intensity = data.get("carbonIntensity", 350)
                        mix = data.get("generationMix", [])
                        for src in mix:
                            energy_mix[src.get("productionType", "other")] = src.get(
                                "percent", 0
                            )
                    else:
                        _LOGGER.warning("electricityMap returned HTTP %s", resp.status)
                        co2_intensity = None
                        energy_mix = {}
            except Exception as e:
                _LOGGER.warning("Failed to fetch electricityMap data: %s", e)
                co2_intensity = None
                energy_mix = {}
        else:
            _LOGGER.debug("No GPS location available, skipping electricityMap call")
            co2_intensity = None
            energy_mix = {}

        # Integrate energy (only when we have real CO2 data)
        now = dt_util.utcnow()
        if self._last_update is not None and co2_intensity is not None:
            dt_hours = (now - self._last_update).total_seconds() / 3600.0
            avg_power = max((charging_power + self._last_power) / 2.0, 0.0)
            delta_energy = avg_power * dt_hours  # kWh
            self._accum_energy += delta_energy
            self._accum_co2 += delta_energy * co2_intensity
            # Histogram
            for src, pct in energy_mix.items():
                self._energy_histogram[src] = (
                    self._energy_histogram.get(src, 0.0) + delta_energy * pct / 100.0
                )
        self._last_update = now
        self._last_power = charging_power

        # Set state and attributes
        self._state = co2_intensity
        self._attrs = {
            "charging_power": charging_power,
            "latitude": latitude,
            "longitude": longitude,
            "energy_mix": energy_mix,
            "accumulated_energy_kwh": round(self._accum_energy, 3),
            "accumulated_co2_g": round(self._accum_co2, 1),
            "energy_histogram": self._energy_histogram,
        }

    @property
    def native_value(self) -> StateType:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs
