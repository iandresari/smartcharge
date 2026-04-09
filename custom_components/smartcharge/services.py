"""Services for EnBW Charging integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN,
    SERVICE_REFRESH_DATA,
)
from .coordinator import EnBWChargingCoordinator

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for EnBW Charging."""

    async def handle_refresh_data(call: ServiceCall) -> None:
        """Handle manual data refresh."""
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, EnBWChargingCoordinator):
                await coordinator.async_refresh()
                _LOGGER.info("Manually refreshed charging station data")

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH_DATA):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH_DATA,
            handle_refresh_data,
        )

    _LOGGER.debug("EnBW Charging services registered")
