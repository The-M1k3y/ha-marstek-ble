"""Declarative data, packet, and entity model for Marstek Venus products."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import (
    SensorDeviceClass,
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
from homeassistant.helpers.entity import EntityCategory

from ..entity import (
    ProductDeviceSpec,
    ProductProfile,
    binary_sensor_entity,
    derived_sensor,
    indexed_sensor_entities,
    sensor_entity,
)
from ..product_runtime import TrackedProductData
from ..schema import (
    DataPath,
    FieldSource,
    PacketSchema,
    bit,
    divide_by,
    divide_each_by,
    nonzero,
    section_field,
    source_field,
    value_field,
)

_DIAGNOSTIC = EntityCategory.DIAGNOSTIC


def _sensor(key: str, name: str, **kwargs: Any):
    return (sensor_entity(key=key, name=name, **kwargs),)


def _binary(key: str, name: str, **kwargs: Any):
    return (binary_sensor_entity(key=key, name=name, **kwargs),)


class VenusPackets:
    """Venus response packet schemas."""

    RUNTIME_INFORMATION = PacketSchema("venus_runtime_information", 0x03, 37)
    DEVICE_INFORMATION = PacketSchema("venus_device_information", 0x04, 1)
    WIFI_SSID = PacketSchema("venus_wifi_ssid", 0x08)
    SYSTEM_DATA = PacketSchema("venus_system_data", 0x0D, 11)
    TIMER_INFORMATION = PacketSchema("venus_timer_information", 0x13, 45)
    BMS_DATA = PacketSchema("venus_bms_data", 0x14, 80)
    CONFIGURATION_DATA = PacketSchema("venus_configuration_data", 0x1A, 17)
    METER_IP = PacketSchema("venus_meter_ip", 0x21, 1)
    CT_POLLING_RATE = PacketSchema("venus_ct_polling_rate", 0x22, 1)
    NETWORK_INFORMATION = PacketSchema("venus_network_information", 0x24)
    LOCAL_API_STATUS = PacketSchema("venus_local_api_status", 0x28, 3)


_RUNTIME = VenusPackets.RUNTIME_INFORMATION
_DEVICE = VenusPackets.DEVICE_INFORMATION
_WIFI = VenusPackets.WIFI_SSID
_SYSTEM = VenusPackets.SYSTEM_DATA
_TIMER = VenusPackets.TIMER_INFORMATION
_BMS = VenusPackets.BMS_DATA
_CONFIG = VenusPackets.CONFIGURATION_DATA
_METER = VenusPackets.METER_IP
_CT = VenusPackets.CT_POLLING_RATE
_NETWORK = VenusPackets.NETWORK_INFORMATION
_LOCAL_API = VenusPackets.LOCAL_API_STATUS


@dataclass(slots=True)
class VenusRuntimeData:
    """Runtime, power, energy, temperature, and connectivity values."""

    out1_power: float | None = source_field(
        sources={_RUNTIME: FieldSource(0x14, "<H", float)},
        entities=_sensor(
            "out1_power",
            "Output 1 Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    temp_low: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x21, "<h", divide_by(10), minimum_length=60
            )
        },
        entities=_sensor(
            "temp_low",
            "Temperature Low",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    temp_high: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x23, "<h", divide_by(10), minimum_length=60
            )
        },
        entities=_sensor(
            "temp_high",
            "Temperature High",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    wifi_connected: bool | None = source_field(
        sources={_RUNTIME: FieldSource(0x0F, "<B", bit(0))},
        entities=_binary(
            "wifi_connected",
            "WiFi Connected",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=_DIAGNOSTIC,
        ),
    )
    mqtt_connected: bool | None = source_field(
        sources={_RUNTIME: FieldSource(0x0F, "<B", bit(1))},
        entities=_binary(
            "mqtt_connected",
            "MQTT Connected",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=_DIAGNOSTIC,
        ),
    )
    out1_active: bool | None = source_field(
        sources={_RUNTIME: FieldSource(0x10, "<B", nonzero)},
        entities=_binary(
            "out1_active",
            "Output 1 Active",
            device_class=BinarySensorDeviceClass.POWER,
            entity_category=_DIAGNOSTIC,
        ),
    )
    extern1_connected: bool | None = source_field(
        sources={_RUNTIME: FieldSource(0x1C, "<B", nonzero)},
        entities=_binary(
            "extern1_connected",
            "External 1 Connected",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
        ),
    )
    grid_power: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(0x00, "<h", float, minimum_length=100)
        },
        entities=_sensor(
            "grid_power",
            "Grid Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    solar_power: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(0x02, "<h", float, minimum_length=100)
        },
        entities=_sensor(
            "solar_power",
            "Solar Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    work_mode: int | None = source_field(
        sources={_RUNTIME: FieldSource(0x04, "<B", minimum_length=100)},
        entities=_sensor("work_mode", "Work Mode", entity_category=_DIAGNOSTIC),
    )
    product_code: int | None = source_field(
        sources={_RUNTIME: FieldSource(0x0C, "<H", minimum_length=100)},
        entities=_sensor(
            "product_code", "Product Code", entity_category=_DIAGNOSTIC
        ),
    )
    power_rating: int | None = source_field(
        sources={_RUNTIME: FieldSource(0x4A, "<H", minimum_length=100)},
        entities=_sensor(
            "power_rating",
            "Power Rating",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            entity_category=_DIAGNOSTIC,
        ),
    )
    daily_energy_charged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(0x0E, "<I", divide_by(100), minimum_length=100)
        },
        entities=_sensor(
            "daily_energy_charged",
            "Daily Energy Charged",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
    )
    monthly_energy_charged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x12, "<I", divide_by(1000), minimum_length=100
            )
        },
        entities=_sensor(
            "monthly_energy_charged",
            "Monthly Energy Charged",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
    )
    daily_energy_discharged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(0x16, "<I", divide_by(100), minimum_length=100)
        },
        entities=_sensor(
            "daily_energy_discharged",
            "Daily Energy Discharged",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
    )
    monthly_energy_discharged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(0x1A, "<I", divide_by(100), minimum_length=100)
        },
        entities=_sensor(
            "monthly_energy_discharged",
            "Monthly Energy Discharged",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
    )
    total_energy_charged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(0x29, "<I", divide_by(100), minimum_length=100)
        },
        entities=_sensor(
            "total_energy_charged",
            "Total Energy Charged",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
    )
    total_energy_discharged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(0x2D, "<I", divide_by(100), minimum_length=100)
        },
        entities=_sensor(
            "total_energy_discharged",
            "Total Energy Discharged",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
    )


@dataclass(slots=True)
class VenusBatteryData:
    """Battery-management values and the fixed sixteen-cell voltage list."""

    bms_version: int | None = source_field(
        sources={_BMS: FieldSource(0x00, "<H")},
        entities=_sensor("bms_version", "BMS Version", entity_category=_DIAGNOSTIC),
    )
    voltage_limit: float | None = source_field(
        sources={_BMS: FieldSource(0x02, "<H", divide_by(10))},
        entities=_sensor(
            "voltage_limit",
            "Voltage Limit",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            entity_category=_DIAGNOSTIC,
        ),
    )
    charge_current_limit: float | None = source_field(
        sources={_BMS: FieldSource(0x04, "<H", divide_by(10))},
        entities=_sensor(
            "charge_current_limit",
            "Charge Current Limit",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            entity_category=_DIAGNOSTIC,
        ),
    )
    discharge_current_limit: float | None = source_field(
        sources={_BMS: FieldSource(0x06, "<h", divide_by(10))},
        entities=_sensor(
            "discharge_current_limit",
            "Discharge Current Limit",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            entity_category=_DIAGNOSTIC,
        ),
    )
    battery_soc: float | None = source_field(
        sources={_BMS: FieldSource(0x08, "<H", float)},
        entities=_sensor(
            "battery_soc",
            "Battery SOC",
            native_unit_of_measurement=PERCENTAGE,
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    battery_soh: float | None = source_field(
        sources={_BMS: FieldSource(0x0A, "<H", float)},
        entities=_sensor(
            "battery_soh",
            "Battery SOH",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    design_capacity: float | None = source_field(
        sources={_BMS: FieldSource(0x0C, "<H", float)},
        entities=_sensor(
            "design_capacity",
            "Design Capacity",
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
        ),
    )
    battery_voltage: float | None = source_field(
        sources={_BMS: FieldSource(0x0E, "<H", divide_by(100))},
        entities=_sensor(
            "battery_voltage",
            "Battery Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
    )
    battery_current: float | None = source_field(
        sources={_BMS: FieldSource(0x10, "<h", divide_by(10))},
        entities=_sensor(
            "battery_current",
            "Battery Current",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    battery_temp: float | None = source_field(
        sources={_BMS: FieldSource(0x12, "<H", float)},
        entities=_sensor(
            "battery_temp",
            "Battery Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    error_code: int | None = source_field(
        sources={_BMS: FieldSource(0x1A, "<H")},
        entities=_sensor("error_code", "Error Code", entity_category=_DIAGNOSTIC),
    )
    warning_code: int | None = source_field(
        sources={_BMS: FieldSource(0x1C, "<I")},
        entities=_sensor(
            "warning_code", "Warning Code", entity_category=_DIAGNOSTIC
        ),
    )
    runtime_hours: float | None = source_field(
        sources={_BMS: FieldSource(0x20, "<I", divide_by(3_600_000))},
        entities=_sensor(
            "runtime_hours",
            "Runtime",
            native_unit_of_measurement=UnitOfTime.HOURS,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_category=_DIAGNOSTIC,
        ),
    )
    mosfet_temp: float | None = source_field(
        sources={_BMS: FieldSource(0x26, "<H", float)},
        entities=_sensor(
            "mosfet_temp",
            "MOSFET Temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    temp_sensor_1: float | None = source_field(
        sources={_BMS: FieldSource(0x28, "<H", float)},
        entities=_sensor(
            "temp_sensor_1",
            "Temperature Sensor 1",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    temp_sensor_2: float | None = source_field(
        sources={_BMS: FieldSource(0x2A, "<H", float)},
        entities=_sensor(
            "temp_sensor_2",
            "Temperature Sensor 2",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    temp_sensor_3: float | None = source_field(
        sources={_BMS: FieldSource(0x2C, "<H", float)},
        entities=_sensor(
            "temp_sensor_3",
            "Temperature Sensor 3",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    temp_sensor_4: float | None = source_field(
        sources={_BMS: FieldSource(0x2E, "<H", float)},
        entities=_sensor(
            "temp_sensor_4",
            "Temperature Sensor 4",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    )
    cell_voltages: list[float | None] = source_field(
        sources={_BMS: FieldSource(0x30, "<16H", divide_each_by(1000))},
        indexed_entities=(
            indexed_sensor_entities(
                16,
                lambda index: SensorEntityDescription(
                    key=f"cell_{index + 1}_voltage",
                    name=f"Cell {index + 1} Voltage",
                    native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                    device_class=SensorDeviceClass.VOLTAGE,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_category=_DIAGNOSTIC,
                    suggested_display_precision=3,
                ),
            ),
        ),
        default_factory=lambda: [None] * 16,
    )


@dataclass(slots=True)
class VenusSystemData:
    system_status: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x00, "<B")},
        entities=_sensor(
            "system_status", "System Status", entity_category=_DIAGNOSTIC
        ),
    )
    system_value_1: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x01, "<H")}
    )
    system_value_2: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x03, "<H")}
    )
    system_value_3: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x05, "<H")}
    )
    system_value_4: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x07, "<H")}
    )
    system_value_5: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x09, "<H")}
    )


@dataclass(slots=True)
class VenusTimerData:
    adaptive_mode_enabled: bool | None = source_field(
        sources={_TIMER: FieldSource(0x00, "<B", nonzero)}
    )
    smart_meter_connected: bool | None = source_field(
        sources={_TIMER: FieldSource(0x25, "<B", nonzero)},
        entities=_binary(
            "smart_meter_connected",
            "Smart Meter Connected",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=_DIAGNOSTIC,
        ),
    )
    adaptive_power_out: float | None = source_field(
        sources={_TIMER: FieldSource(0x26, "<H", float)}
    )


@dataclass(slots=True)
class VenusConfigurationData:
    config_mode: int | None = source_field(
        sources={_CONFIG: FieldSource(0x00, "<B")},
        entities=_sensor(
            "config_mode", "Config Mode", entity_category=_DIAGNOSTIC
        ),
    )
    config_status: int | None = source_field(
        sources={_CONFIG: FieldSource(0x04, "<b")}
    )
    config_value: int | None = source_field(
        sources={_CONFIG: FieldSource(0x10, "<B")}
    )
    ct_polling_rate: int | None = source_field(
        sources={_CT: FieldSource(0x00, "<B")},
        entities=_sensor(
            "ct_polling_rate", "CT Polling Rate", entity_category=_DIAGNOSTIC
        ),
    )


@dataclass(slots=True)
class VenusDeviceInformation:
    device_type: str | None = value_field(
        entities=_sensor(
            "device_type", "Device Type", entity_category=_DIAGNOSTIC
        )
    )
    device_id: str | None = value_field(
        entities=_sensor("device_id", "Device ID", entity_category=_DIAGNOSTIC)
    )
    serial_number: str | None = value_field(
        entities=_sensor(
            "serial_number", "Serial Number", entity_category=_DIAGNOSTIC
        )
    )
    mac_address: str | None = value_field(
        entities=_sensor(
            "mac_address", "MAC Address", entity_category=_DIAGNOSTIC
        )
    )
    firmware_version: str | None = value_field(
        entities=_sensor(
            "firmware_version", "Firmware Version", entity_category=_DIAGNOSTIC
        )
    )
    hardware_version: str | None = value_field(
        entities=_sensor(
            "hardware_version", "Hardware Version", entity_category=_DIAGNOSTIC
        )
    )


@dataclass(slots=True)
class VenusNetworkData:
    wifi_ssid: str | None = value_field(
        entities=_sensor("wifi_ssid", "WiFi SSID", entity_category=_DIAGNOSTIC)
    )
    meter_ip: str | None = value_field(
        entities=_sensor("meter_ip", "Meter IP", entity_category=_DIAGNOSTIC)
    )
    network_info: str | None = value_field(
        entities=_sensor(
            "network_info", "Network Info", entity_category=_DIAGNOSTIC
        )
    )
    ip_address: str | None = value_field(
        entities=_sensor(
            "ip_address", "IP Address", entity_category=_DIAGNOSTIC
        )
    )
    gateway: str | None = value_field(
        entities=_sensor("gateway", "Gateway", entity_category=_DIAGNOSTIC)
    )
    subnet_mask: str | None = value_field(
        entities=_sensor(
            "subnet_mask", "Subnet Mask", entity_category=_DIAGNOSTIC
        )
    )
    dns_server: str | None = value_field(
        entities=_sensor(
            "dns_server", "DNS Server", entity_category=_DIAGNOSTIC
        )
    )
    local_api_status: str | None = None


_FLAT_FIELD_PATHS: dict[str, DataPath] = {
    **{
        name: ("runtime", name)
        for name in (
            "out1_power",
            "temp_low",
            "temp_high",
            "wifi_connected",
            "mqtt_connected",
            "out1_active",
            "extern1_connected",
            "grid_power",
            "solar_power",
            "work_mode",
            "product_code",
            "power_rating",
            "daily_energy_charged",
            "monthly_energy_charged",
            "daily_energy_discharged",
            "monthly_energy_discharged",
            "total_energy_charged",
            "total_energy_discharged",
        )
    },
    **{
        name: ("battery", name)
        for name in (
            "bms_version",
            "voltage_limit",
            "charge_current_limit",
            "discharge_current_limit",
            "battery_soc",
            "battery_soh",
            "design_capacity",
            "battery_voltage",
            "battery_current",
            "battery_temp",
            "error_code",
            "warning_code",
            "runtime_hours",
            "mosfet_temp",
            "temp_sensor_1",
            "temp_sensor_2",
            "temp_sensor_3",
            "temp_sensor_4",
            "cell_voltages",
        )
    },
    **{
        name: ("system", name)
        for name in (
            "system_status",
            "system_value_1",
            "system_value_2",
            "system_value_3",
            "system_value_4",
            "system_value_5",
        )
    },
    **{
        name: ("timer", name)
        for name in (
            "adaptive_mode_enabled",
            "smart_meter_connected",
            "adaptive_power_out",
        )
    },
    **{
        name: ("configuration", name)
        for name in (
            "config_mode",
            "config_status",
            "config_value",
            "ct_polling_rate",
        )
    },
    **{
        name: ("device", name)
        for name in (
            "device_type",
            "device_id",
            "serial_number",
            "mac_address",
            "firmware_version",
            "hardware_version",
        )
    },
    **{
        name: ("network", name)
        for name in (
            "wifi_ssid",
            "meter_ip",
            "network_info",
            "ip_address",
            "gateway",
            "subnet_mask",
            "dns_server",
            "local_api_status",
        )
    },
}


@dataclass(slots=True)
class VenusData(TrackedProductData):
    """Cumulative data snapshot for one Venus device."""

    runtime: VenusRuntimeData = section_field(VenusRuntimeData)
    battery: VenusBatteryData = section_field(VenusBatteryData)
    system: VenusSystemData = section_field(VenusSystemData)
    timer: VenusTimerData = section_field(VenusTimerData)
    configuration: VenusConfigurationData = section_field(VenusConfigurationData)
    device: VenusDeviceInformation = section_field(VenusDeviceInformation)
    network: VenusNetworkData = section_field(VenusNetworkData)
    field_updates: dict[str, dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )

    def __getattr__(self, name: str) -> Any:
        """Expose legacy flat reads while entity platforms are migrated."""

        path = _FLAT_FIELD_PATHS.get(name)
        if path is None:
            raise AttributeError(name)

        value: Any = self
        for part in path:
            value = getattr(value, part)
        return value

    def _metadata_aliases(self, path: DataPath) -> tuple[str, ...]:
        aliases = super()._metadata_aliases(path)
        if path == ("battery", "cell_voltages"):
            return (
                *aliases,
                *(f"cell_{index + 1}_voltage" for index in range(16)),
            )
        return aliases


def _battery_power(data: VenusData) -> float | None:
    voltage = data.battery.battery_voltage
    current = data.battery.battery_current
    return (
        voltage * current
        if voltage is not None and current is not None
        else None
    )


def _capacity(data: VenusData, available: bool) -> float | None:
    soc = data.battery.battery_soc
    capacity = data.battery.design_capacity
    if soc is None or capacity is None:
        return None
    return ((100 - soc) if available else soc) / 100 * capacity


VENUS_PROFILE = ProductProfile(
    product_id="venus",
    device=ProductDeviceSpec("Marstek", "Venus E"),
    data_type=VenusData,
    packets=(
        _RUNTIME,
        _DEVICE,
        _WIFI,
        _SYSTEM,
        _TIMER,
        _BMS,
        _CONFIG,
        _METER,
        _CT,
        _NETWORK,
        _LOCAL_API,
    ),
    supported_commands=frozenset(
        {0x03, 0x08, 0x0D, 0x13, 0x14, 0x1A, 0x1C, 0x21, 0x22, 0x24, 0x28}
    ),
    discovery_prefixes=("MST_ACCP_", "MST_VNSE3_"),
    derived_entities=(
        derived_sensor(
            description=SensorEntityDescription(
                key="battery_power",
                name="Battery Power",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            value_fn=_battery_power,
            stale_paths=(
                ("battery", "battery_voltage"),
                ("battery", "battery_current"),
            ),
        ),
        derived_sensor(
            description=SensorEntityDescription(
                key="battery_power_in",
                name="Battery Power In",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            value_fn=lambda data: (
                max(0, value)
                if (value := _battery_power(data)) is not None
                else None
            ),
            stale_paths=(
                ("battery", "battery_voltage"),
                ("battery", "battery_current"),
            ),
        ),
        derived_sensor(
            description=SensorEntityDescription(
                key="battery_power_out",
                name="Battery Power Out",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            value_fn=lambda data: (
                max(0, -value)
                if (value := _battery_power(data)) is not None
                else None
            ),
            stale_paths=(
                ("battery", "battery_voltage"),
                ("battery", "battery_current"),
            ),
        ),
        derived_sensor(
            description=SensorEntityDescription(
                key="remaining_capacity",
                name="Remaining Capacity",
                native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
                device_class=SensorDeviceClass.ENERGY_STORAGE,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            value_fn=lambda data: _capacity(data, False),
            stale_paths=(
                ("battery", "battery_soc"),
                ("battery", "design_capacity"),
            ),
        ),
        derived_sensor(
            description=SensorEntityDescription(
                key="available_capacity",
                name="Available Capacity",
                native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
                device_class=SensorDeviceClass.ENERGY_STORAGE,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            value_fn=lambda data: _capacity(data, True),
            stale_paths=(
                ("battery", "battery_soc"),
                ("battery", "design_capacity"),
            ),
        ),
    ),
)
