"""The SmartCharge integration."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import (
    CONF_STATIC_FRIENDLY_NAME,
    CONF_STATION_ID,
    DOMAIN,
    HUB_CARS_ID,
    HUB_STATIONS_ID,
    PLATFORM_SENSOR,
)
from .coordinator import EnBWChargingCoordinator
from .services import async_setup_services

_LOGGER: logging.Logger = logging.getLogger(__name__)

PLATFORMS: Final = [PLATFORM_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartCharge from a config entry."""
    _LOGGER.debug("Setting up SmartCharge integration")

    hass.data.setdefault(DOMAIN, {})

    dev_reg = dr.async_get(hass)

    if entry.data.get("entry_type") == "car":
        hass.data[DOMAIN][entry.entry_id] = None
        # Ensure the shared "Cars" hub exists, then register the car as a child.
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, HUB_CARS_ID)},
            name="Cars",
            model="SmartCharge Cars Hub",
        )
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get("car_name", "Car"),
            model="Electric Vehicle",
            via_device=(DOMAIN, HUB_CARS_ID),
        )
    else:
        session = async_get_clientsession(hass)
        coordinator = EnBWChargingCoordinator(hass, session, entry)
        await coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][entry.entry_id] = coordinator
        # Ensure the shared "Charging Stations" hub exists, then register
        # the station as a child.
        station_id = entry.data.get(CONF_STATION_ID, "")
        station_display_name = entry.data.get(CONF_STATIC_FRIENDLY_NAME) or station_id
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, HUB_STATIONS_ID)},
            name="Charging Stations",
            model="SmartCharge Stations Hub",
        )
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, station_id)},
            name=station_display_name,
            model="Charging Station",
            via_device=(DOMAIN, HUB_STATIONS_ID),
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if entry.data.get("entry_type") != "car":
        # Clean up orphaned entities from older versions of the integration.
        ent_reg = er.async_get(hass)
        entities = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
        station_id = entry.data.get(CONF_STATION_ID, "")
        expected_unique_id = f"{station_id}_availability"
        for entity in entities:
            if entity.unique_id != expected_unique_id:
                _LOGGER.info(
                    "Removing orphaned entity %s (unique_id=%s)",
                    entity.entity_id,
                    entity.unique_id,
                )
                ent_reg.async_remove(entity.entity_id)

    await async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and clean up entities for car or station."""
    if entry.data.get("entry_type") == "car":
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id, None)
        return unload_ok

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up persistent storage when a config entry is removed."""
    if entry.data.get("entry_type") == "car":
        # Entity registry cleanup is handled automatically by HA core.
        _LOGGER.debug("Removed car entry for car %s", entry.data.get("car_name"))
        return

    station_id = entry.data.get(CONF_STATION_ID, "unknown")
    store = Store(hass, 1, f"{DOMAIN}.statistics.{station_id}")
    await store.async_remove()
    _LOGGER.debug("Removed persistent statistics for station %s", station_id)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
