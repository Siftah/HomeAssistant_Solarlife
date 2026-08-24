"""SolarLife BLE protocol helpers."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from bleak import BleakClient

_LOGGER = logging.getLogger(__name__)

NOTIFY_HANDLE: Final = 0x11
WRITE_HANDLE: Final = 0x14

SLAVE_ID: Final = 0x01
READ_INPUT_REGISTERS: Final = 0x04
LIVE_DATA_START: Final = 0x3000
LIVE_DATA_COUNT: Final = 0x007C
# a Modbus function-4 reply carries two bytes per register, plus
# slave id + function + byte count + 2 CRC bytes
EXPECTED_BYTE_COUNT: Final = LIVE_DATA_COUNT * 2
EXPECTED_FRAME_LEN: Final = EXPECTED_BYTE_COUNT + 5

REQUEST_TIMEOUT: Final = 20


class SolarLifeProtocolError(Exception):
    """Raised when the SolarLife controller returns invalid data."""


def _u16_be(data: bytearray | bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def _crc_modbus(data: bytes | bytearray) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


def _build_request(slave_id: int, function_code: int, address: int, count: int) -> bytes:
    payload = bytearray(
        (
            slave_id,
            function_code,
            address >> 8,
            address & 0xFF,
            count >> 8,
            count & 0xFF,
        )
    )
    crc = _crc_modbus(payload)
    payload.extend((crc & 0xFF, crc >> 8))
    return bytes(payload)



def _find_frame(buffer: bytearray) -> bytes | None:
    """Return the first complete, CRC-valid response frame in `buffer`.

    The controller can leave bytes from an earlier exchange in its transmit
    buffer, so the first notification chunk is NOT guaranteed to be the start of
    our response -- a stray 5-byte fragment ahead of the real 253-byte frame was
    observed in practice. The old code took `buffer[2]` as the byte count no
    matter what, so one stray leading byte desynchronised the whole read: it
    either sliced the wrong window (CRC failure) or waited for a length that
    never arrived (20 s timeout).

    Resynchronise on the header we know we asked for instead of trusting the
    stream to be aligned, and confirm with the CRC before accepting a frame.
    """
    header = bytes((SLAVE_ID, READ_INPUT_REGISTERS, EXPECTED_BYTE_COUNT))
    start = 0
    while (index := buffer.find(header, start)) != -1:
        if len(buffer) - index < EXPECTED_FRAME_LEN:
            return None  # header found, body still arriving
        frame = bytes(buffer[index : index + EXPECTED_FRAME_LEN])
        if _crc_modbus(frame[:-2]) == (frame[-2] | (frame[-1] << 8)):
            if index:
                _LOGGER.debug("Skipped %d stray leading byte(s)", index)
            return frame
        start = index + 1  # header pattern occurring inside the payload
    return None


def _dump_services(client: "BleakClient") -> None:
    """Log the full GATT table once, at debug level."""
    for service in client.services:
        _LOGGER.debug("service %s (%s)", service.uuid, service.description)
        for char in service.characteristics:
            _LOGGER.debug(
                "  char handle=0x%02x uuid=%s props=%s",
                char.handle,
                char.uuid,
                ",".join(char.properties),
            )
            for desc in char.descriptors:
                _LOGGER.debug("    desc handle=0x%02x uuid=%s", desc.handle, desc.uuid)


def _resolve_notify_char(client: "BleakClient"):
    """Return the characteristic that carries controller responses.

    Handles are only stable for a given firmware, so prefer the documented
    handle but fall back to the first notify/indicate characteristic.
    """
    if _LOGGER.isEnabledFor(logging.DEBUG):
        _dump_services(client)
    char = client.services.get_characteristic(NOTIFY_HANDLE)
    if char is not None and (
        "notify" in char.properties or "indicate" in char.properties
    ):
        return char
    for service in client.services:
        for candidate in service.characteristics:
            if "notify" in candidate.properties or "indicate" in candidate.properties:
                _LOGGER.debug(
                    "Falling back to notify characteristic 0x%02x (%s)",
                    candidate.handle,
                    candidate.uuid,
                )
                return candidate
    raise SolarLifeProtocolError("no notify characteristic found on the controller")


def _resolve_write_char(client: "BleakClient"):
    """Return the characteristic used to send Modbus requests."""
    char = client.services.get_characteristic(WRITE_HANDLE)
    if char is not None and (
        "write" in char.properties or "write-without-response" in char.properties
    ):
        return char
    for service in client.services:
        for candidate in service.characteristics:
            if (
                "write" in candidate.properties
                or "write-without-response" in candidate.properties
            ):
                _LOGGER.debug(
                    "Falling back to write characteristic 0x%02x (%s)",
                    candidate.handle,
                    candidate.uuid,
                )
                return candidate
    raise SolarLifeProtocolError("no writable characteristic found on the controller")


async def async_read_controller_data(client: "BleakClient") -> dict[str, float | int]:
    """Read and parse a full SolarLife live data frame."""
    loop = asyncio.get_running_loop()
    future: asyncio.Future[bytes] = loop.create_future()
    receive_buffer = bytearray()

    def notification_handler(_handle: int, data: bytearray) -> None:
        if future.done():
            return

        receive_buffer.extend(data)
        _LOGGER.debug(
            "Received SolarLife BLE notification chunk: %d bytes, %d buffered",
            len(data),
            len(receive_buffer),
        )
        frame = _find_frame(receive_buffer)
        if frame is not None:
            _LOGGER.debug("Received complete SolarLife frame: %d bytes", len(frame))
            future.set_result(frame)

    notify_char = _resolve_notify_char(client)
    write_char = _resolve_write_char(client)
    _LOGGER.debug(
        "SolarLife GATT resolved: notify handle 0x%02x (%s), write handle 0x%02x (%s)",
        notify_char.handle,
        notify_char.uuid,
        write_char.handle,
        write_char.uuid,
    )

    await client.start_notify(notify_char, notification_handler)
    try:
        # NOTE: the original code wrote b"\x01\x00" to handle 0x12 here. 0x12 is
        # the CCCD *descriptor* of the notify characteristic, not a characteristic,
        # so bleak raises BleakCharacteristicNotFoundError. start_notify() already
        # writes that descriptor, so the extra write is redundant as well as wrong.
        _LOGGER.debug(
            "Writing SolarLife live-data request to handle 0x%02x", write_char.handle
        )
        await client.write_gatt_char(
            write_char,
            _build_request(
                SLAVE_ID,
                READ_INPUT_REGISTERS,
                LIVE_DATA_START,
                LIVE_DATA_COUNT,
            ),
            response="write" in write_char.properties,
        )
        frame = await asyncio.wait_for(future, REQUEST_TIMEOUT)
    finally:
        _LOGGER.debug("Stopping SolarLife notifications on handle 0x%02x", notify_char.handle)
        await client.stop_notify(notify_char)

    return parse_live_data_frame(frame, LIVE_DATA_START)


def parse_live_data_frame(frame: bytes, base_address: int) -> dict[str, float | int]:
    """Parse a SolarLife Modbus response frame."""
    if len(frame) < 5:
        raise SolarLifeProtocolError("response frame is too short")

    byte_count = frame[2]
    expected_length = byte_count + 5
    if len(frame) != expected_length:
        raise SolarLifeProtocolError(
            f"response frame length {len(frame)} does not match expected {expected_length}"
        )

    expected_crc = frame[-2] | (frame[-1] << 8)
    actual_crc = _crc_modbus(frame[:-2])
    if expected_crc != actual_crc:
        raise SolarLifeProtocolError("response CRC check failed")

    values: dict[str, float | int] = {}
    raw_values: dict[int, int] = {}
    register_count = byte_count // 2
    for offset in range(register_count):
        register_address = base_address + offset
        raw_values[register_address] = _u16_be(frame, 3 + offset * 2)
        definition = REGISTER_DEFINITIONS.get(register_address)
        if definition is None:
            continue

        key, scale = definition
        raw_value = raw_values[register_address]
        values[key] = raw_value / scale if scale != 1 else raw_value

    for key, low_address, high_address, scale in COMBINED_REGISTER_DEFINITIONS:
        if low_address in raw_values and high_address in raw_values:
            raw_value = raw_values[low_address] | (raw_values[high_address] << 16)
            values[key] = raw_value / scale if scale != 1 else raw_value

    return values


REGISTER_DEFINITIONS: Final[dict[int, tuple[str, int]]] = {
    0x3000: ("pv_rated_voltage", 100),
    0x3001: ("pv_rated_current", 100),
    0x3002: ("pv_rated_power_l", 100),
    0x3003: ("pv_rated_power_h", 100),
    0x3004: ("battery_rated_voltage", 100),
    0x3005: ("battery_rated_current", 100),
    0x3006: ("battery_rated_power_l", 100),
    0x3007: ("battery_rated_power_h", 100),
    0x3008: ("load_rated_voltage", 100),
    0x3009: ("load_rated_current", 100),
    0x300A: ("load_rated_power_l", 100),
    0x300B: ("load_rated_power_h", 100),
    0x3030: ("slave_id", 1),
    0x3031: ("running_days", 1),
    0x3032: ("sys_voltage", 100),
    0x3033: ("battery_status", 1),
    0x3034: ("charge_status", 1),
    0x3035: ("discharge_status", 1),
    0x3036: ("env_temperature", 100),
    0x3037: ("sys_temperature", 100),
    0x3038: ("undervoltage_times", 1),
    0x3039: ("fullycharged_times", 1),
    0x303A: ("overvoltage_prot_times", 1),
    0x303B: ("overcurrent_prot_times", 1),
    0x303C: ("shortcircuit_prot_times", 1),
    0x303D: ("opencircuit_prot_times", 1),
    0x303E: ("hw_prot_times", 1),
    0x303F: ("charge_overtemp_prot_times", 1),
    0x3040: ("discharge_overtemp_prot_times", 1),
    0x3045: ("battery_remaining_capacity", 1),
    0x3046: ("battery_voltage", 100),
    0x3047: ("battery_current", 100),
    0x3048: ("battery_power_lo", 100),
    0x3049: ("battery_power_hi", 100),
    0x304A: ("load_voltage", 100),
    0x304B: ("load_current", 100),
    0x304C: ("load_power_l", 100),
    0x304D: ("load_power_h", 100),
    0x304E: ("solar_voltage", 100),
    0x304F: ("solar_current", 100),
    0x3050: ("solar_power_l", 100),
    0x3051: ("solar_power_h", 100),
    0x3052: ("daily_production", 100),
    0x3053: ("total_production_l", 100),
    0x3054: ("total_production_h", 100),
    0x3055: ("daily_consumption", 100),
    0x3056: ("total_consumption_l", 100),
    0x3057: ("total_consumption_h", 100),
    0x3058: ("lighttime_daily", 1),
    0x305D: ("monthly_production_l", 100),
    0x305E: ("monthly_production_h", 100),
    0x305F: ("yearly_production_l", 100),
    0x3060: ("yearly_production_h", 100),
}

COMBINED_REGISTER_DEFINITIONS: Final[tuple[tuple[str, int, int, int], ...]] = (
    ("pv_rated_power", 0x3002, 0x3003, 100),
    ("battery_rated_power", 0x3006, 0x3007, 100),
    ("load_rated_power", 0x300A, 0x300B, 100),
    ("battery_power", 0x3048, 0x3049, 100),
    ("load_power", 0x304C, 0x304D, 100),
    ("solar_power", 0x3050, 0x3051, 100),
    ("total_production", 0x3053, 0x3054, 100),
    ("total_consumption", 0x3056, 0x3057, 100),
    ("monthly_production", 0x305D, 0x305E, 100),
    ("yearly_production", 0x305F, 0x3060, 100),
)
