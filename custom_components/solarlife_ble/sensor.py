"""Sensor platform for SolarLife BLE."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SolarLifeConfigEntry
from .const import DOMAIN
from .coordinator import SolarLifeDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class SolarLifeSensorEntityDescription(SensorEntityDescription):
    """SolarLife sensor description."""

    value_key: str


SENSORS: tuple[SolarLifeSensorEntityDescription, ...] = (
    SolarLifeSensorEntityDescription(
        key="battery_voltage",
        value_key="battery_voltage",
        translation_key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="battery_current",
        value_key="battery_current",
        translation_key="battery_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="battery_power",
        value_key="battery_power",
        translation_key="battery_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="battery_remaining_capacity",
        value_key="battery_remaining_capacity",
        translation_key="battery_remaining_capacity",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="solar_voltage",
        value_key="solar_voltage",
        translation_key="solar_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="solar_current",
        value_key="solar_current",
        translation_key="solar_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="solar_power",
        value_key="solar_power",
        translation_key="solar_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="load_voltage",
        value_key="load_voltage",
        translation_key="load_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="load_current",
        value_key="load_current",
        translation_key="load_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="load_power",
        value_key="load_power",
        translation_key="load_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="daily_production",
        value_key="daily_production",
        translation_key="daily_production",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SolarLifeSensorEntityDescription(
        key="total_production",
        value_key="total_production",
        translation_key="total_production",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SolarLifeSensorEntityDescription(
        key="daily_consumption",
        value_key="daily_consumption",
        translation_key="daily_consumption",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SolarLifeSensorEntityDescription(
        key="total_consumption",
        value_key="total_consumption",
        translation_key="total_consumption",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SolarLifeSensorEntityDescription(
        key="env_temperature",
        value_key="env_temperature",
        translation_key="env_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="sys_temperature",
        value_key="sys_temperature",
        translation_key="sys_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolarLifeSensorEntityDescription(
        key="running_days",
        value_key="running_days",
        translation_key="running_days",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarLifeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolarLife sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SolarLifeSensor(coordinator, description) for description in SENSORS
    )


class SolarLifeSensor(CoordinatorEntity[SolarLifeDataUpdateCoordinator], SensorEntity):
    """SolarLife sensor entity."""

    entity_description: SolarLifeSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SolarLifeDataUpdateCoordinator,
        description: SolarLifeSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.name,
            manufacturer="SolarLife",
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
        )

    @property
    def native_value(self) -> float | int | None:
        """Return the native value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.value_key)
