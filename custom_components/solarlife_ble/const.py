"""Constants for the SolarLife BLE integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "solarlife_ble"

CONF_ADDRESS = "address"

DEFAULT_NAME = "SolarLife Controller"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
MANUFACTURER_ID = 0x03A0
LOCAL_NAME = "SolarLife"
SERVICE_UUIDS = [
    "0000fee7-0000-1000-8000-00805f9b34fb",
    "4953ff00-fe7d-4ae5-8fa9-9fafd205e455",
]

PLATFORMS = ["sensor"]
