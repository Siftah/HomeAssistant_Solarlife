"""Data coordinator for SolarLife BLE."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from bleak import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_ADDRESS, DEFAULT_SCAN_INTERVAL, DOMAIN
from .protocol import SolarLifeProtocolError, async_read_controller_data

_LOGGER = logging.getLogger(__name__)


class SolarLifeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, float | int]]):
    """Fetch SolarLife controller data over Home Assistant Bluetooth."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.address: str = entry.data[CONF_ADDRESS]
        self.name: str = entry.data[CONF_NAME]
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, float | int]:
        """Poll the controller."""
        _LOGGER.debug("Looking up connectable SolarLife BLE device %s", self.address)
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            _LOGGER.debug(
                "No connectable Bluetooth route is currently available for %s",
                self.address,
            )
            raise UpdateFailed(
                f"Bluetooth device {self.address} is not available from a connectable adapter"
            )

        try:
            data = await self._async_read_device(device)
        except (asyncio.TimeoutError, BleakError, SolarLifeProtocolError) as err:
            _LOGGER.debug("SolarLife BLE update failed for %s", self.address, exc_info=True)
            raise UpdateFailed(f"Failed to read SolarLife controller: {err}") from err

        _LOGGER.debug("Read %d SolarLife values from %s", len(data), self.address)
        return data

    async def _async_read_device(self, device: BLEDevice) -> dict[str, float | int]:
        """Read data from a BLE device."""
        disconnect_callback: Callable[[BleakClientWithServiceCache], None] = (
            lambda _client: None
        )
        _LOGGER.debug("Connecting to SolarLife BLE device %s", self.address)
        client = await establish_connection(
            BleakClientWithServiceCache,
            device,
            self.address,
            disconnect_callback,
            use_services_cache=True,
            ble_device_callback=lambda: bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            ),
            timeout=10,
        )

        try:
            _LOGGER.debug("Connected to SolarLife BLE device %s; reading data", self.address)
            return await async_read_controller_data(client)
        finally:
            _LOGGER.debug("Disconnecting from SolarLife BLE device %s", self.address)
            await client.disconnect()
