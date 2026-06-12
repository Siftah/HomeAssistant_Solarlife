"""Constants for the SolarLife BLE integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "solarlife_ble"

CONF_ADDRESS = "address"

DEFAULT_NAME = "SolarLife Controller"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

PLATFORMS = ["sensor"]

