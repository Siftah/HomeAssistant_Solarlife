"""Config flow for SolarLife BLE."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ADDRESS,
    DEFAULT_NAME,
    DOMAIN,
    LOCAL_NAME,
    MANUFACTURER_ID,
    SERVICE_UUIDS,
)

_MAC_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")


class SolarLifeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SolarLife BLE."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            name = user_input.get(CONF_NAME) or DEFAULT_NAME

            if not _MAC_RE.match(address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={CONF_ADDRESS: address, CONF_NAME: name},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle Bluetooth discovery."""
        if not _is_solarlife_device(discovery_info):
            return self.async_abort(reason="not_solarlife_device")

        address = discovery_info.address.upper()
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {"name": discovery_info.name or LOCAL_NAME}

        if not discovery_info.connectable:
            return self.async_abort(reason="not_connectable")

        return self.async_create_entry(
            title=discovery_info.name or DEFAULT_NAME,
            data={
                CONF_ADDRESS: address,
                CONF_NAME: discovery_info.name or DEFAULT_NAME,
            },
        )


def _is_solarlife_device(discovery_info: BluetoothServiceInfoBleak) -> bool:
    """Return whether the discovered BLE advertisement matches SolarLife."""
    if discovery_info.name != LOCAL_NAME:
        return False
    if MANUFACTURER_ID not in discovery_info.manufacturer_data:
        return False
    return bool(set(discovery_info.service_uuids).intersection(SERVICE_UUIDS))
