"""Sensor platform for Marstek BLE integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
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
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MarstekDataUpdateCoordinator
from .product_entity_platform import (
    EntityBinding,
    EntityPlatform,
    setup_product_entity_platform,
)

_LOGGER = logging.getLogger(__name__)
VERBOSE_LOGGER = logging.getLogger(f"{__name__}.verbose")
VERBOSE_LOGGER.propagate = False
VERBOSE_LOGGER.setLevel(logging.INFO)
STALE_AFTER_SECONDS = 10 * 60

_LEGACY_SENSOR_SPECS = (
    ("battery_voltage", "Battery Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE),
    ("battery_current", "Battery Current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT),
    ("battery_soc", "Battery SOC", PERCENTAGE, SensorDeviceClass.BATTERY),
    ("battery_soh", "Battery SOH", PERCENTAGE, None),
    ("battery_temp", "Battery Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("battery_power", "Battery Power", UnitOfPower.WATT, SensorDeviceClass.POWER),
    ("grid_power", "Grid Power", UnitOfPower.WATT, SensorDeviceClass.POWER),
    ("solar_power", "Solar Power", UnitOfPower.WATT, SensorDeviceClass.POWER),
    ("battery_power_in", "Battery Power In", UnitOfPower.WATT, SensorDeviceClass.POWER),
    ("battery_power_out", "Battery Power Out", UnitOfPower.WATT, SensorDeviceClass.POWER),
    ("out1_power", "Output 1 Power", UnitOfPower.WATT, SensorDeviceClass.POWER),
    ("daily_energy_charged", "Daily Energy Charged", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY),
    ("daily_energy_discharged", "Daily Energy Discharged", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY),
    ("monthly_energy_charged", "Monthly Energy Charged", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY),
    ("monthly_energy_discharged", "Monthly Energy Discharged", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY),
    ("total_energy_charged", "Total Energy Charged", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY),
    ("total_energy_discharged", "Total Energy Discharged", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY),
    ("design_capacity", "Design Capacity", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY),
    ("remaining_capacity", "Remaining Capacity", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY_STORAGE),
    ("available_capacity", "Available Capacity", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY_STORAGE),
    ("temp_low", "Temperature Low", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("temp_high", "Temperature High", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("mosfet_temp", "MOSFET Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("temp_sensor_1", "Temperature Sensor 1", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("temp_sensor_2", "Temperature Sensor 2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("temp_sensor_3", "Temperature Sensor 3", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("temp_sensor_4", "Temperature Sensor 4", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("system_status", "System Status", None, None),
    ("config_mode", "Config Mode", None, None),
    ("ct_polling_rate", "CT Polling Rate", None, None),
    ("work_mode", "Work Mode", None, None),
    ("product_code", "Product Code", None, None),
    ("power_rating", "Power Rating", UnitOfPower.WATT, SensorDeviceClass.POWER),
    ("bms_version", "BMS Version", None, None),
    ("voltage_limit", "Voltage Limit", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE),
    ("charge_current_limit", "Charge Current Limit", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT),
    ("discharge_current_limit", "Discharge Current Limit", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT),
    ("error_code", "Error Code", None, None),
    ("warning_code", "Warning Code", None, None),
    ("runtime_hours", "Runtime", UnitOfTime.HOURS, SensorDeviceClass.DURATION),
)

_LEGACY_TEXT_SPECS = (
    ("battery_state", "Battery State"),
    ("device_type", "Device Type"),
    ("device_id", "Device ID"),
    ("serial_number", "Serial Number"),
    ("mac_address", "MAC Address"),
    ("firmware_version", "Firmware Version"),
    ("hardware_version", "Hardware Version"),
    ("wifi_ssid", "WiFi SSID"),
    ("network_info", "Network Info"),
    ("ip_address", "IP Address"),
    ("gateway", "Gateway"),
    ("subnet_mask", "Subnet Mask"),
    ("dns_server", "DNS Server"),
    ("meter_ip", "Meter IP"),
)


def _legacy_value(key: str):
    """Return a value getter matching the historical flat Venus entities."""

    if key == "battery_power":
        return lambda data: (
            data.battery_voltage * data.battery_current
            if data.battery_voltage is not None and data.battery_current is not None
            else None
        )
    if key == "battery_power_in":
        return lambda data: (
            max(0, data.battery_voltage * data.battery_current)
            if data.battery_voltage is not None and data.battery_current is not None
            else None
        )
    if key == "battery_power_out":
        return lambda data: (
            max(0, -(data.battery_voltage * data.battery_current))
            if data.battery_voltage is not None and data.battery_current is not None
            else None
        )
    if key == "remaining_capacity":
        return lambda data: (
            (data.battery_soc / 100.0) * data.design_capacity
            if data.battery_soc is not None and data.design_capacity is not None
            else None
        )
    if key == "available_capacity":
        return lambda data: (
            ((100.0 - data.battery_soc) / 100.0) * data.design_capacity
            if data.battery_soc is not None and data.design_capacity is not None
            else None
        )
    if key == "battery_state":
        return lambda data: (
            "charging"
            if data.battery_voltage is not None
            and data.battery_current is not None
            and data.battery_voltage * data.battery_current > 5
            else "discharging"
            if data.battery_voltage is not None
            and data.battery_current is not None
            and data.battery_voltage * data.battery_current < -5
            else "inactive"
        )
    return lambda data, attribute=key: getattr(data, attribute)


def _setup_legacy_sensors(
    coordinator: MarstekDataUpdateCoordinator,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the historical flat Venus entity contract."""

    entities: list[MarstekSensor] = []
    for key, name, unit, device_class in _LEGACY_SENSOR_SPECS:
        stale_fields = None
        if key in {"battery_power", "battery_power_in", "battery_power_out"}:
            stale_fields = ["battery_voltage", "battery_current"]
        elif key in {"remaining_capacity", "available_capacity"}:
            stale_fields = ["battery_soc", "design_capacity"]
        state_class = (
            SensorStateClass.TOTAL_INCREASING
            if key.startswith(("daily_energy_", "monthly_energy_", "total_energy_"))
            or key == "runtime_hours"
            else SensorStateClass.MEASUREMENT
            if device_class not in {None, SensorDeviceClass.ENERGY}
            else None
        )
        entities.append(
            MarstekSensor(
                coordinator,
                entry,
                key,
                name,
                _legacy_value(key),
                unit,
                device_class,
                state_class,
                stale_fields=stale_fields,
            )
        )

    for index in range(16):
        entities.append(
            MarstekSensor(
                coordinator,
                entry,
                f"cell_{index + 1}_voltage",
                f"Cell {index + 1} Voltage",
                lambda data, idx=index: (
                    data.cell_voltages[idx]
                    if data.cell_voltages and idx < len(data.cell_voltages)
                    else None
                ),
                UnitOfElectricPotential.VOLT,
                SensorDeviceClass.VOLTAGE,
                SensorStateClass.MEASUREMENT,
                suggested_display_precision=2,
            )
        )

    for key, name in _LEGACY_TEXT_SPECS:
        stale_fields = ["battery_voltage", "battery_current"] if key == "battery_state" else None
        entities.append(
            MarstekTextSensor(
                coordinator,
                entry,
                key,
                name,
                _legacy_value(key),
                stale_fields=stale_fields,
            )
        )

    async_add_entities(entities)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Marstek BLE sensors from a config entry."""

    coordinator = entry.runtime_data
    if not hasattr(coordinator, "product") and not hasattr(coordinator.data, "battery"):
        _setup_legacy_sensors(coordinator, entry, async_add_entities)
        return

    setup_product_entity_platform(
        coordinator,
        entry,
        async_add_entities,
        EntityPlatform.SENSOR,
        MarstekSensor,
    )

    if coordinator.product.product_id == "venus":
        async_add_entities(
            [
                MarstekTextSensor(
                    coordinator,
                    entry,
                    "battery_state",
                    "Battery State",
                    _legacy_value("battery_state"),
                    stale_fields=["battery_voltage", "battery_current"],
                )
            ]
        )


class MarstekSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Marstek sensor."""

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str | EntityBinding,
        name: str | None = None,
        value_fn=None,
        unit: str | None = None,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
        entity_category: EntityCategory | None = None,
        suggested_display_precision: int | None = None,
        stale_fields: list[str] | None = None,
    ) -> None:
        """Initialize a declarative or legacy sensor."""

        super().__init__(coordinator)
        self._binding: EntityBinding | None = key if isinstance(key, EntityBinding) else None
        self._legacy_value_fn = value_fn

        if self._binding is not None:
            description = self._binding.description
            self._key = self._binding.unique_key
            self._stale_fields: tuple[Any, ...] = self._binding.stale_paths
            self._attr_entity_description = description
            self._attr_name = description.name
            self._attr_has_entity_name = True
            self._attr_native_unit_of_measurement = getattr(
                description, "native_unit_of_measurement", None
            )
            self._attr_device_class = getattr(description, "device_class", None)
            self._attr_state_class = getattr(description, "state_class", None)
            self._attr_entity_category = getattr(description, "entity_category", None)
            precision = getattr(description, "suggested_display_precision", None)
            if precision is not None:
                self._attr_suggested_display_precision = precision
        else:
            self._key = key
            self._stale_fields = tuple(stale_fields or [key])
            self._attr_name = name
            self._attr_has_entity_name = True
            self._attr_native_unit_of_measurement = unit
            self._attr_device_class = device_class
            self._attr_state_class = state_class
            self._attr_entity_category = entity_category
            if suggested_display_precision is not None:
                self._attr_suggested_display_precision = suggested_display_precision

        self._attr_unique_id = f"{entry.entry_id}_{self._key}"

    def _handle_coordinator_update(self) -> None:
        """Handle updated data with telemetry for debugging staleness."""

        value = self.native_value
        meta = self._get_representative_metadata()
        VERBOSE_LOGGER.debug(
            "[%s/%s] Sensor update %s=%s (source=%s ts=%s age=%.1fs payload=%s)",
            self.coordinator.device_name,
            self.coordinator.address,
            self._key,
            value,
            meta.get("command_hex") if meta else "unknown",
            meta.get("timestamp") if meta else "unknown",
            meta.get("age_seconds", -1) if meta else -1,
            meta.get("payload_hex") if meta else "unknown",
        )
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return whether the sensor currently has a valid product binding."""

        if not (super().available and self.coordinator.data is not None):
            return False
        if self._binding is not None and not self._binding.is_present(self.coordinator.data):
            return False
        age = self._stale_age_seconds()
        return age is None or age <= STALE_AFTER_SECONDS

    @property
    def native_value(self):
        """Return the state of the sensor."""

        if self._binding is not None:
            return self._binding.value_from(self.coordinator.data)
        return self._legacy_value_fn(self.coordinator.data)

    def _stale_age_seconds(self) -> float | None:
        """Return the oldest dependency age in seconds if available."""

        data = self.coordinator.data
        if data is None:
            return None
        getter = getattr(data, "get_field_metadata", None)
        if getter is None:
            return None

        ages: list[float] = []
        for field in self._stale_fields:
            meta = getter(field)
            if not meta or meta.get("age_seconds") is None:
                continue
            ages.append(meta["age_seconds"])
        return max(ages) if ages else None

    def _get_representative_metadata(self) -> dict | None:
        """Return metadata for logging from the first available field."""

        data = self.coordinator.data
        if data is None:
            return None
        getter = getattr(data, "get_field_metadata", None)
        if getter is None:
            return None
        for field in self._stale_fields:
            meta = getter(field)
            if meta:
                return meta
        return None

    @property
    def device_info(self):
        """Return product-aware device information."""

        if self._binding is None:
            return {
                "identifiers": {(DOMAIN, self.coordinator.ble_device.address)},
                "connections": {
                    (CONNECTION_BLUETOOTH, self.coordinator.ble_device.address)
                },
                "name": self.coordinator.device_name,
                "manufacturer": "Marstek",
                "model": "Venus E",
            }

        device = self._binding.device
        main_identifier = self.coordinator.address
        info = {
            "identifiers": {(DOMAIN, device.identifier(main_identifier))},
            "name": device.name or self.coordinator.device_name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        if device.parent_key is None:
            info["connections"] = {(CONNECTION_BLUETOOTH, main_identifier)}
        else:
            info["via_device"] = (DOMAIN, main_identifier)
        return info


class MarstekTextSensor(MarstekSensor):
    """Legacy text-sensor constructor retained for existing callers and tests."""

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        value_fn,
        entity_category: EntityCategory | None = None,
        stale_fields: list[str] | None = None,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            key,
            name,
            value_fn,
            entity_category=entity_category,
            stale_fields=stale_fields,
        )

    @property
    def native_value(self):
        """Return the legacy text state as a string."""

        value = super().native_value
        return str(value) if value is not None else None
