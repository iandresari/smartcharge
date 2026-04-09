"""The SmartCharge integration."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    PLATFORM_BINARY_SENSOR,
    PLATFORM_DEVICE_TRACKER,
    PLATFORM_SENSOR,
)
from .coordinator import EnBWChargingCoordinator
from .services import async_setup_services

_LOGGER: logging.Logger = logging.getLogger(__name__)

PLATFORMS: Final = [PLATFORM_SENSOR, PLATFORM_BINARY_SENSOR, PLATFORM_DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EnBW Charging from a config entry."""
    _LOGGER.debug("Setting up EnBW Charging integration")

    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    coordinator = EnBWChargingCoordinator(hass, session, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
