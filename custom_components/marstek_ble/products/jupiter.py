"""Declarative data, packet, entity, and expansion model for Jupiter-C Plus.

Only sanitized protocol structure is represented here. Raw diagnostic frames,
captured values, timestamps, identifiers, network names, and event contents are
intentionally excluded. This module is not wired into the integration yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfFrequency, UnitOfPower, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from ..entity import ProductDeviceSpec, ProductProfile, RepeatedChildDeviceSpec, binary_sensor_entity, derived_sensor, sensor_entity
from ..schema import FieldSource, PacketSchema, RepeatedSectionSource, divide_by, multiply_by, nonzero, repeated_section_field, section_field, source_field, value_field

_DIAGNOSTIC = EntityCategory.DIAGNOSTIC
_BATTERY_STATES = {0: "idle", 1: "charging", 2: "discharging"}


def _sensor(key: str, name: str, **kwargs):
    return (sensor_entity(key=key, name=name, **kwargs),)


def _binary(key: str, name: str, **kwargs):
    return (binary_sensor_entity(key=key, name=name, **kwargs),)


def _battery_state(value: int) -> str:
    return _BATTERY_STATES.get(value, "unknown")


class JupiterPackets:
    """Observed Jupiter-C Plus response schemas."""

    RUNTIME_INFORMATION = PacketSchema("jupiter_runtime_information", 0x03, 74, 74)
    DEVICE_INFORMATION = PacketSchema("jupiter_device_information", 0x04)
    WIFI_SSID = PacketSchema("jupiter_wifi_ssid", 0x08)
    UNRESOLVED_STATUS = PacketSchema("jupiter_unresolved_status", 0x0D, 12, 12)
    EVENT_HISTORY = PacketSchema("jupiter_event_history", 0x13, 160, 160)
    DETAILED_TELEMETRY = PacketSchema("jupiter_detailed_telemetry", 0x14, 166, 166)
    RAW_STATUS_21 = PacketSchema("jupiter_raw_status_21", 0x21, 1, 1)
    RAW_STATUS_22 = PacketSchema("jupiter_raw_status_22", 0x22, 1, 1)
    RAW_STATUS_24 = PacketSchema("jupiter_raw_status_24", 0x24, 1, 1)


_RUNTIME = JupiterPackets.RUNTIME_INFORMATION
_DETAIL = JupiterPackets.DETAILED_TELEMETRY
_EVENTS = JupiterPackets.EVENT_HISTORY


@dataclass(slots=True)
class JupiterPvInputData:
    """One of four identical PV input records."""

    power: float | None = source_field(
        sources={_RUNTIME: FieldSource(0x00, "<H", float), _DETAIL: FieldSource(0x04, "<H", divide_by(10))},
        entities=_sensor("power", "Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    )
    connected: bool | None = source_field(
        sources={_RUNTIME: FieldSource(0x02, "<B", nonzero)},
        entities=_binary("connected", "Connected", device_class=BinarySensorDeviceClass.CONNECTIVITY),
    )
    voltage: float | None = source_field(
        sources={_DETAIL: FieldSource(0x00, "<H", divide_by(10))},
        entities=_sensor("voltage", "Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    )
    current: float | None = source_field(
        sources={_DETAIL: FieldSource(0x02, "<H", divide_by(10))},
        entities=_sensor("current", "Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    )


@dataclass(slots=True)
class JupiterRuntimeData:
    """Live system and battery summary values."""

    ac_output_power: float | None = source_field(sources={_RUNTIME: FieldSource(0x0C, "<H", float), _DETAIL: FieldSource(0x10, "<h", float)}, entities=_sensor("ac_output_power", "AC Output Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT))
    grid_connection_valid: bool | None = source_field(sources={_RUNTIME: FieldSource(0x0E, "<B", nonzero)}, entities=_binary("grid_connection_valid", "Grid Connection Valid", device_class=BinarySensorDeviceClass.CONNECTIVITY))
    # Temporary data-model compatibility for callers using the old field name.
    ac_output_active: bool | None = source_field(sources={_RUNTIME: FieldSource(0x0E, "<B", nonzero)})
    battery_state: str | None = source_field(sources={_RUNTIME: FieldSource(0x12, "<B", _battery_state)}, entities=_sensor("battery_state", "Battery State"))
    stored_battery_energy: float | None = source_field(sources={_RUNTIME: FieldSource(0x13, "<H", multiply_by(10)), _DETAIL: FieldSource(0x78, "<H", float)}, entities=_sensor("stored_battery_energy", "Stored Battery Energy", native_unit_of_measurement=UnitOfEnergy.WATT_HOUR, device_class=SensorDeviceClass.ENERGY_STORAGE, state_class=SensorStateClass.MEASUREMENT))
    battery_soc: float | None = source_field(sources={_RUNTIME: FieldSource(0x15, "<B", float), _DETAIL: FieldSource(0x5E, "<H", float)}, entities=_sensor("battery_soc", "Battery SOC", native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT))
    operational_status: int | None = source_field(sources={_RUNTIME: FieldSource(0x3C, "<B")}, entities=_sensor("operational_status", "Operational Status", entity_category=_DIAGNOSTIC))
    ems_firmware_version: int | None = source_field(sources={_RUNTIME: FieldSource(0x2F, "<H")}, entities=_sensor("ems_firmware_version", "EMS Firmware Version", entity_category=_DIAGNOSTIC))
    inverter_firmware_version: int | None = source_field(sources={_RUNTIME: FieldSource(0x31, "<H")}, entities=_sensor("inverter_firmware_version", "Inverter Firmware Version", entity_category=_DIAGNOSTIC))
    mppt_firmware_version: int | None = source_field(sources={_RUNTIME: FieldSource(0x33, "<H")}, entities=_sensor("mppt_firmware_version", "MPPT Firmware Version", entity_category=_DIAGNOSTIC))
    bms_firmware_version: int | None = source_field(sources={_RUNTIME: FieldSource(0x35, "<H"), _DETAIL: FieldSource(0x64, "<H")}, entities=_sensor("bms_firmware_version", "BMS Firmware Version", entity_category=_DIAGNOSTIC))

    @property
    def battery_charging_active(self) -> bool | None:
        if self.battery_state in (None, "unknown"):
            return None
        return self.battery_state == "charging"


@dataclass(slots=True)
class JupiterEnergyData:
    """PV-generation and discharge-energy counters."""

    daily_pv_generation: float | None = source_field(sources={_RUNTIME: FieldSource(0x17, "<I", divide_by(100)), _DETAIL: FieldSource(0x40, "<I", divide_by(100))}, entities=_sensor("daily_pv_generation", "Daily PV Generation", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING))
    monthly_pv_generation: float | None = source_field(sources={_RUNTIME: FieldSource(0x1B, "<I", divide_by(100)), _DETAIL: FieldSource(0x48, "<I", divide_by(100))}, entities=_sensor("monthly_pv_generation", "Monthly PV Generation", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING))
    total_pv_generation: float | None = source_field(sources={_RUNTIME: FieldSource(0x1F, "<I", divide_by(100)), _DETAIL: FieldSource(0x4C, "<I", divide_by(100))}, entities=_sensor("total_pv_generation", "Total PV Generation", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING))
    daily_discharge_energy: float | None = source_field(sources={_RUNTIME: FieldSource(0x27, "<I", divide_by(100)), _DETAIL: FieldSource(0x14, "<I", divide_by(100))}, entities=_sensor("daily_discharge_energy", "Daily Discharge Energy", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING))
    monthly_discharge_energy: float | None = source_field(sources={_RUNTIME: FieldSource(0x2B, "<I", divide_by(100)), _DETAIL: FieldSource(0x1C, "<I", divide_by(100))}, entities=_sensor("monthly_discharge_energy", "Monthly Discharge Energy", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING))
    local_total_discharge_energy: float | None = source_field(sources={_DETAIL: FieldSource(0x18, "<I", divide_by(100))}, entities=_sensor("local_total_discharge_energy", "Local Total Discharge Energy", native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING, entity_category=_DIAGNOSTIC))


@dataclass(slots=True)
class JupiterInverterData:
    """Inverter and grid-side detailed telemetry."""

    state_flags: int | None = source_field(sources={_DETAIL: FieldSource(0x00, "<H")}, entities=_sensor("inverter_state_flags", "Inverter State Flags", entity_category=_DIAGNOSTIC))
    # Error-code names inferred from controlled grid-loss behavior remain tentative.
    error_code: int | None = source_field(sources={_RUNTIME: FieldSource(0x23, "<H"), _DETAIL: FieldSource(0x02, "<H")}, entities=_sensor("inverter_error_code", "Inverter Error Code", entity_category=_DIAGNOSTIC))
    warning_code: int | None = source_field(sources={_DETAIL: FieldSource(0x04, "<H")}, entities=_sensor("inverter_warning_code", "Inverter Warning Code", entity_category=_DIAGNOSTIC))
    grid_voltage: float | None = source_field(sources={_DETAIL: FieldSource(0x06, "<H", divide_by(10))}, entities=_sensor("grid_voltage", "Grid Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT))
    grid_current: float | None = source_field(sources={_DETAIL: FieldSource(0x08, "<H", divide_by(10))})
    grid_power_factor: int | None = source_field(sources={_DETAIL: FieldSource(0x0A, "<H")}, entities=_sensor("grid_power_factor", "Grid Power Factor", entity_category=_DIAGNOSTIC))
    grid_frequency: float | None = source_field(sources={_DETAIL: FieldSource(0x0C, "<H", divide_by(100))}, entities=_sensor("grid_frequency", "Grid Frequency", native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2))
    bus_voltage: float | None = source_field(sources={_DETAIL: FieldSource(0x0E, "<H", divide_by(10))}, entities=_sensor("bus_voltage", "Internal Bus Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, entity_category=_DIAGNOSTIC))
    temperature: float | None = source_field(sources={_DETAIL: FieldSource(0x12, "<h", float)}, entities=_sensor("inverter_temperature", "Inverter Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT))


@dataclass(slots=True)
class JupiterMpptData:
    """MPPT controller and DC-output telemetry."""

    state_flags: int | None = source_field(sources={_DETAIL: FieldSource(0x20, "<H")}, entities=_sensor("mppt_state_flags", "MPPT State Flags", entity_category=_DIAGNOSTIC))
    error_code: int | None = source_field(sources={_DETAIL: FieldSource(0x22, "<H")}, entities=_sensor("mppt_error_code", "MPPT Error Code", entity_category=_DIAGNOSTIC))
    temperature: float | None = source_field(sources={_DETAIL: FieldSource(0x24, "<h", float)}, entities=_sensor("mppt_temperature", "MPPT Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT))
    warning_code: int | None = source_field(sources={_DETAIL: FieldSource(0x26, "<H")}, entities=_sensor("mppt_warning_code", "MPPT Warning Code", entity_category=_DIAGNOSTIC))
    dc_output_voltage: float | None = source_field(sources={_DETAIL: FieldSource(0x50, "<H", divide_by(10))}, entities=_sensor("mppt_dc_output_voltage", "MPPT DC Output Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, entity_category=_DIAGNOSTIC))
    dc_output_current: float | None = source_field(sources={_DETAIL: FieldSource(0x52, "<h", divide_by(10))}, entities=_sensor("mppt_dc_output_current", "MPPT DC Output Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, entity_category=_DIAGNOSTIC))


@dataclass(slots=True)
class JupiterBatteryPackData:
    """One base or expansion battery summary record."""

    highest_cell_index: int | None = source_field(sources={_DETAIL: FieldSource(0x00, "<B")}, entities=_sensor("highest_cell_index", "Highest Cell Index", entity_category=_DIAGNOSTIC))
    lowest_cell_index: int | None = source_field(sources={_DETAIL: FieldSource(0x01, "<B")}, entities=_sensor("lowest_cell_index", "Lowest Cell Index", entity_category=_DIAGNOSTIC))
    highest_cell_voltage: float | None = source_field(sources={_DETAIL: FieldSource(0x02, "<H", divide_by(1000))}, entities=_sensor("highest_cell_voltage", "Highest Cell Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3))
    lowest_cell_voltage: float | None = source_field(sources={_DETAIL: FieldSource(0x04, "<H", divide_by(1000))}, entities=_sensor("lowest_cell_voltage", "Lowest Cell Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3))
    status: int | None = source_field(sources={_DETAIL: FieldSource(0x06, "<H")}, entities=_sensor("status", "Status", entity_category=_DIAGNOSTIC))


_BATTERY_CHILDREN = RepeatedChildDeviceSpec(
    key_prefix="battery_pack",
    model="Jupiter-C Battery Pack",
    name_factory=lambda index: "Base Battery" if index == 0 else f"Expansion Battery {index}",
    identifier_factory=lambda index: f"battery_pack:{index}",
)


@dataclass(slots=True)
class JupiterBatteryData:
    """Aggregate BMS telemetry and four fixed battery-pack slots."""

    charge_voltage_limit: float | None = source_field(sources={_DETAIL: FieldSource(0x58, "<H", divide_by(10))}, entities=_sensor("charge_voltage_limit", "Charge Voltage Limit", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, entity_category=_DIAGNOSTIC))
    charge_current_limit: float | None = source_field(sources={_DETAIL: FieldSource(0x5A, "<H", divide_by(10))}, entities=_sensor("charge_current_limit", "Charge Current Limit", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, entity_category=_DIAGNOSTIC))
    discharge_current_limit: float | None = source_field(sources={_DETAIL: FieldSource(0x5C, "<H", divide_by(10))}, entities=_sensor("discharge_current_limit", "Discharge Current Limit", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, entity_category=_DIAGNOSTIC))
    soh: float | None = source_field(sources={_DETAIL: FieldSource(0x60, "<H", float)}, entities=_sensor("battery_soh", "Battery SOH", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT))
    rated_capacity: float | None = source_field(sources={_DETAIL: FieldSource(0x62, "<H", float)}, entities=_sensor("rated_capacity", "Rated Battery Capacity", native_unit_of_measurement=UnitOfEnergy.WATT_HOUR, device_class=SensorDeviceClass.ENERGY))
    voltage: float | None = source_field(sources={_DETAIL: FieldSource(0x66, "<H", divide_by(100))}, entities=_sensor("battery_voltage", "Battery Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2))
    current: float | None = source_field(sources={_DETAIL: FieldSource(0x68, "<h", divide_by(10))}, entities=_sensor("battery_current", "Battery Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT))
    temperature: float | None = source_field(sources={_DETAIL: FieldSource(0x6A, "<h", divide_by(10))}, entities=_sensor("battery_temperature", "Battery Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT))
    error_code_1: int | None = source_field(sources={_DETAIL: FieldSource(0x6C, "<H")}, entities=_sensor("bms_error_code_1", "BMS Error Code 1", entity_category=_DIAGNOSTIC))
    warning_code_1: int | None = source_field(sources={_DETAIL: FieldSource(0x6E, "<H")}, entities=_sensor("bms_warning_code_1", "BMS Warning Code 1", entity_category=_DIAGNOSTIC))
    error_code_2: int | None = source_field(sources={_DETAIL: FieldSource(0x70, "<H")}, entities=_sensor("bms_error_code_2", "BMS Error Code 2", entity_category=_DIAGNOSTIC))
    warning_code_2: int | None = source_field(sources={_DETAIL: FieldSource(0x72, "<H")}, entities=_sensor("bms_warning_code_2", "BMS Warning Code 2", entity_category=_DIAGNOSTIC))
    cell_flags: int | None = source_field(sources={_DETAIL: FieldSource(0x74, "<B")}, entities=_sensor("cell_flags", "Cell Flags", entity_category=_DIAGNOSTIC))
    status_flags: int | None = source_field(sources={_DETAIL: FieldSource(0x75, "<B")}, entities=_sensor("bms_status_flags", "BMS Status Flags", entity_category=_DIAGNOSTIC))
    pack_count: int | None = source_field(sources={_DETAIL: FieldSource(0x76, "<H")}, entities=_sensor("battery_pack_count", "Battery Pack Count", entity_category=_DIAGNOSTIC))
    packs: list[JupiterBatteryPackData] = repeated_section_field(JupiterBatteryPackData, count=4, sources={_DETAIL: RepeatedSectionSource(0x7A, 8)}, active_count_attribute="pack_count", child_device=_BATTERY_CHILDREN)
    temp_sensor_1: float | None = source_field(sources={_DETAIL: FieldSource(0x9A, "<h", float)}, entities=_sensor("battery_temp_sensor_1", "Battery Temperature Sensor 1", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, entity_category=_DIAGNOSTIC))
    temp_sensor_2: float | None = source_field(sources={_DETAIL: FieldSource(0x9C, "<h", float)}, entities=_sensor("battery_temp_sensor_2", "Battery Temperature Sensor 2", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, entity_category=_DIAGNOSTIC))
    temp_sensor_3: float | None = source_field(sources={_DETAIL: FieldSource(0x9E, "<h", float)}, entities=_sensor("battery_temp_sensor_3", "Battery Temperature Sensor 3", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, entity_category=_DIAGNOSTIC))
    temp_sensor_4: float | None = source_field(sources={_DETAIL: FieldSource(0xA0, "<h", float)}, entities=_sensor("battery_temp_sensor_4", "Battery Temperature Sensor 4", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, entity_category=_DIAGNOSTIC))
    environment_temperature: float | None = source_field(sources={_DETAIL: FieldSource(0xA2, "<h", float)}, entities=_sensor("bms_environment_temperature", "BMS Environment Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, entity_category=_DIAGNOSTIC))
    mosfet_temperature: float | None = source_field(sources={_DETAIL: FieldSource(0xA4, "<h", float)}, entities=_sensor("bms_mosfet_temperature", "BMS MOSFET Temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, entity_category=_DIAGNOSTIC))


@dataclass(slots=True)
class JupiterEventRecord:
    """One event-history record with a raw 16-bit event/error code."""

    year: int | None = source_field(sources={_EVENTS: FieldSource(0x00, "<H")})
    month: int | None = source_field(sources={_EVENTS: FieldSource(0x02, "<B")})
    day: int | None = source_field(sources={_EVENTS: FieldSource(0x03, "<B")})
    hour: int | None = source_field(sources={_EVENTS: FieldSource(0x04, "<B")})
    minute: int | None = source_field(sources={_EVENTS: FieldSource(0x05, "<B")})
    event_code: int | None = source_field(sources={_EVENTS: FieldSource(0x06, "<H")})
    # Temporary compatibility fields preserve the previous byte-wise view.
    event_value: int | None = source_field(sources={_EVENTS: FieldSource(0x06, "<B")})
    event_state: int | None = source_field(sources={_EVENTS: FieldSource(0x07, "<B")})


@dataclass(slots=True)
class JupiterIdentityData:
    device_type: str | None = value_field(entities=_sensor("device_type", "Device Type", entity_category=_DIAGNOSTIC))
    device_id: str | None = value_field(entities=_sensor("device_id", "Device ID", entity_category=_DIAGNOSTIC))
    mac_address: str | None = value_field(entities=_sensor("mac_address", "Bluetooth MAC Address", entity_category=_DIAGNOSTIC))
    wifi_ssid: str | None = value_field(entities=_sensor("wifi_ssid", "WiFi SSID", entity_category=_DIAGNOSTIC))


@dataclass(slots=True)
class JupiterRawStatusData:
    status_21: int | None = source_field(sources={JupiterPackets.RAW_STATUS_21: FieldSource(0, "<B")})
    status_22: int | None = source_field(sources={JupiterPackets.RAW_STATUS_22: FieldSource(0, "<B")})
    status_24: int | None = source_field(sources={JupiterPackets.RAW_STATUS_24: FieldSource(0, "<B")})


@dataclass(slots=True)
class JupiterData:
    """Cumulative Jupiter-C Plus data and fixed expansion slots."""

    runtime: JupiterRuntimeData = section_field(JupiterRuntimeData)
    energy: JupiterEnergyData = section_field(JupiterEnergyData)
    inverter: JupiterInverterData = section_field(JupiterInverterData)
    mppt: JupiterMpptData = section_field(JupiterMpptData)
    pv_inputs: list[JupiterPvInputData] = repeated_section_field(JupiterPvInputData, count=4, sources={_RUNTIME: RepeatedSectionSource(0, 3), _DETAIL: RepeatedSectionSource(0x28, 6)}, item_name_factory=lambda index: f"PV Input {index + 1}")
    battery: JupiterBatteryData = section_field(JupiterBatteryData)
    events: list[JupiterEventRecord] = repeated_section_field(JupiterEventRecord, count=20, sources={_EVENTS: RepeatedSectionSource(0, 8)})
    identity: JupiterIdentityData = section_field(JupiterIdentityData)
    raw_status: JupiterRawStatusData = section_field(JupiterRawStatusData)


def _battery_power(data: JupiterData) -> float | None:
    if data.battery.voltage is None or data.battery.current is None:
        return None
    return data.battery.voltage * data.battery.current


JUPITER_PROFILE = ProductProfile(
    product_id="jupiter_c_plus",
    device=ProductDeviceSpec("Marstek", "Jupiter-C Plus", "JPLS"),
    data_type=JupiterData,
    packets=(JupiterPackets.RUNTIME_INFORMATION, JupiterPackets.DEVICE_INFORMATION, JupiterPackets.WIFI_SSID, JupiterPackets.UNRESOLVED_STATUS, JupiterPackets.EVENT_HISTORY, JupiterPackets.DETAILED_TELEMETRY, JupiterPackets.RAW_STATUS_21, JupiterPackets.RAW_STATUS_22, JupiterPackets.RAW_STATUS_24),
    discovery_prefixes=("MST_JPLS_",),
    derived_entities=(
        derived_sensor(description=SensorEntityDescription(key="battery_power", name="Battery Power", native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT), value_fn=_battery_power, stale_paths=(("battery", "voltage"), ("battery", "current"))),
    ),
)
