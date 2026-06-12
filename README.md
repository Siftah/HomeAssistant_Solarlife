# SolarLife BLE Home Assistant Integration

[![HACS](https://github.com/siftah/ha-solarlife-ble/actions/workflows/hacs.yml/badge.svg)](https://github.com/siftah/ha-solarlife-ble/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/siftah/ha-solarlife-ble/actions/workflows/hassfest.yml/badge.svg)](https://github.com/siftah/ha-solarlife-ble/actions/workflows/hassfest.yml)

Custom Home Assistant integration for SolarLife-compatible Bluetooth solar charge
controllers, based on the protocol work from
[majonezz/solarlife](https://github.com/majonezz/solarlife).

Unlike the original C utility, this integration does not publish to MQTT. It uses
Home Assistant's Bluetooth stack, so a connectable adapter or ESPHome Bluetooth
proxy can make the BLE connection and the integration exposes native sensor
entities directly in Home Assistant.

## Install

### HACS

1. Open HACS.
2. Select **Custom repositories**.
3. Add this repository URL.
4. Select **Integration** as the category.
5. Install **SolarLife BLE** and restart Home Assistant.

### Manual

Copy `custom_components/solarlife_ble` into your Home Assistant
`config/custom_components` directory and restart Home Assistant.

## Configure

Home Assistant should discover controllers that advertise as `SolarLife` with
manufacturer ID `928` and service UUID `0000fee7-0000-1000-8000-00805f9b34fb`
or `4953ff00-fe7d-4ae5-8fa9-9fafd205e455`.

If discovery does not appear, add the integration from
**Settings > Devices & services > Add integration** and enter the Bluetooth MAC
address of the controller.

You need a connectable Bluetooth path to the controller. A local Bluetooth
adapter works, and an ESPHome Bluetooth proxy should also work when it supports
outgoing connections.

## Troubleshooting

If setup or updates report that no backend has an available connection slot, Home
Assistant has discovered the controller but cannot currently open an active BLE
connection through any proxy or adapter. Common causes are:

- the controller is near the edge of Bluetooth range
- the ESPHome proxy has no free active connection slots
- the last advertisement is stale, so Home Assistant no longer has a fresh
  connectable path

Move a connectable proxy closer to the controller, reduce other active BLE
connections on that proxy, or add another ESPHome Bluetooth proxy near the
controller.

## HACS readiness

This repository is structured as a HACS integration repository:

- one integration under `custom_components/solarlife_ble`
- root `hacs.json`
- integration `manifest.json` with required HACS metadata
- HACS and Hassfest GitHub Actions
- local brand metadata and icon assets

For inclusion as a default HACS repository, the public GitHub repository should
also have issues enabled, useful topics, a repository description, and at least
one GitHub release after validation passes.

## Notes

Known SolarLife advertisements look like this:

- name: `SolarLife`
- manufacturer ID: `928`
- manufacturer data: controller MAC address bytes
- service UUIDs: `0000fee7-0000-1000-8000-00805f9b34fb`,
  `4953ff00-fe7d-4ae5-8fa9-9fafd205e455`

The integration polls register block `0x3000` through `0x307B` using the same
GATT handles and Modbus CRC/request framing as the original project.

## License

GPL-2.0-only. This project is derived from the GPL-2.0
[majonezz/solarlife](https://github.com/majonezz/solarlife) protocol work.
