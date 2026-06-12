"""SolarLife BLE integration."""

from __future__ import annotations

from typing import TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import SolarLifeDataUpdateCoordinator

SolarLifeConfigEntry: TypeAlias = ConfigEntry[SolarLifeDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SolarLifeConfigEntry) -> bool:
    """Set up SolarLife BLE from a config entry."""
    coordinator = SolarLifeDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SolarLifeConfigEntry) -> bool:
    """Unload a SolarLife BLE config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
