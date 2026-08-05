"""Declarative data model for the Marstek Venus series.

The model mirrors the fields currently exposed by the integration while keeping
all fixed-layout packet representations next to their destination fields. It is
not wired into the existing protocol parser yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..schema import (
    FieldSource,
    PacketSchema,
    bit,
    divide_by,
    divide_each_by,
    nonzero,
    section_field,
    source_field,
)


class VenusPackets:
    """Packet schemas currently used for fixed-layout Venus telemetry."""

    RUNTIME_INFORMATION = PacketSchema(
        name="venus_runtime_information",
        command=0x03,
        minimum_length=37,
    )
    SYSTEM_DATA = PacketSchema(
        name="venus_system_data",
        command=0x0D,
        minimum_length=11,
    )
    TIMER_INFORMATION = PacketSchema(
        name="venus_timer_information",
        command=0x13,
        minimum_length=45,
    )
    BMS_DATA = PacketSchema(
        name="venus_bms_data",
        command=0x14,
        minimum_length=80,
    )
    CONFIGURATION_DATA = PacketSchema(
        name="venus_configuration_data",
        command=0x1A,
        minimum_length=17,
    )
    CT_POLLING_RATE = PacketSchema(
        name="venus_ct_polling_rate",
        command=0x22,
        minimum_length=1,
    )


_RUNTIME = VenusPackets.RUNTIME_INFORMATION
_SYSTEM = VenusPackets.SYSTEM_DATA
_TIMER = VenusPackets.TIMER_INFORMATION
_BMS = VenusPackets.BMS_DATA
_CONFIGURATION = VenusPackets.CONFIGURATION_DATA
_CT_POLLING_RATE = VenusPackets.CT_POLLING_RATE


@dataclass(slots=True)
class VenusRuntimeData:
    """Runtime, power, energy, and connectivity values from command 0x03."""

    out1_power: float | None = source_field(
        sources={_RUNTIME: FieldSource(0x14, "<H", float)},
    )
    temp_low: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x21,
                "<h",
                divide_by(10),
                minimum_length=60,
            )
        },
    )
    temp_high: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x23,
                "<h",
                divide_by(10),
                minimum_length=60,
            )
        },
    )
    wifi_connected: bool | None = source_field(
        sources={_RUNTIME: FieldSource(0x0F, "<B", bit(0))},
    )
    mqtt_connected: bool | None = source_field(
        sources={_RUNTIME: FieldSource(0x0F, "<B", bit(1))},
    )
    out1_active: bool | None = source_field(
        sources={_RUNTIME: FieldSource(0x10, "<B", nonzero)},
    )
    extern1_connected: bool | None = source_field(
        sources={_RUNTIME: FieldSource(0x1C, "<B", nonzero)},
    )
    grid_power: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x00,
                "<h",
                float,
                minimum_length=100,
            )
        },
    )
    solar_power: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x02,
                "<h",
                float,
                minimum_length=100,
            )
        },
    )
    work_mode: int | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x04,
                "<B",
                minimum_length=100,
            )
        },
    )
    product_code: int | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x0C,
                "<H",
                minimum_length=100,
            )
        },
    )
    power_rating: int | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x4A,
                "<H",
                minimum_length=100,
            )
        },
    )
    daily_energy_charged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x0E,
                "<I",
                divide_by(100),
                minimum_length=100,
            )
        },
    )
    daily_energy_discharged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x16,
                "<I",
                divide_by(100),
                minimum_length=100,
            )
        },
    )
    monthly_energy_charged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x12,
                "<I",
                divide_by(1000),
                minimum_length=100,
            )
        },
    )
    monthly_energy_discharged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x1A,
                "<I",
                divide_by(100),
                minimum_length=100,
            )
        },
    )
    total_energy_charged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x29,
                "<I",
                divide_by(100),
                minimum_length=100,
            )
        },
    )
    total_energy_discharged: float | None = source_field(
        sources={
            _RUNTIME: FieldSource(
                0x2D,
                "<I",
                divide_by(100),
                minimum_length=100,
            )
        },
    )


@dataclass(slots=True)
class VenusBatteryData:
    """Battery-management values from command 0x14."""

    battery_soc: float | None = source_field(
        sources={_BMS: FieldSource(0x08, "<H", float)},
    )
    battery_soh: float | None = source_field(
        sources={_BMS: FieldSource(0x0A, "<H", float)},
    )
    design_capacity: float | None = source_field(
        sources={_BMS: FieldSource(0x0C, "<H", float)},
    )
    battery_voltage: float | None = source_field(
        sources={_BMS: FieldSource(0x0E, "<H", divide_by(100))},
    )
    battery_current: float | None = source_field(
        sources={_BMS: FieldSource(0x10, "<h", divide_by(10))},
    )
    battery_temp: float | None = source_field(
        sources={_BMS: FieldSource(0x12, "<H", float)},
    )
    bms_version: int | None = source_field(
        sources={_BMS: FieldSource(0x00, "<H")},
    )
    voltage_limit: float | None = source_field(
        sources={_BMS: FieldSource(0x02, "<H", divide_by(10))},
    )
    charge_current_limit: float | None = source_field(
        sources={_BMS: FieldSource(0x04, "<H", divide_by(10))},
    )
    discharge_current_limit: float | None = source_field(
        sources={_BMS: FieldSource(0x06, "<h", divide_by(10))},
    )
    error_code: int | None = source_field(
        sources={_BMS: FieldSource(0x1A, "<H")},
    )
    warning_code: int | None = source_field(
        sources={_BMS: FieldSource(0x1C, "<I")},
    )
    runtime_hours: float | None = source_field(
        sources={_BMS: FieldSource(0x20, "<I", divide_by(3_600_000))},
    )
    mosfet_temp: float | None = source_field(
        sources={_BMS: FieldSource(0x26, "<H", float)},
    )
    temp_sensor_1: float | None = source_field(
        sources={_BMS: FieldSource(0x28, "<H", float)},
    )
    temp_sensor_2: float | None = source_field(
        sources={_BMS: FieldSource(0x2A, "<H", float)},
    )
    temp_sensor_3: float | None = source_field(
        sources={_BMS: FieldSource(0x2C, "<H", float)},
    )
    temp_sensor_4: float | None = source_field(
        sources={_BMS: FieldSource(0x2E, "<H", float)},
    )
    cell_voltages: list[float | None] = source_field(
        sources={
            _BMS: FieldSource(
                0x30,
                "<16H",
                divide_each_by(1000),
            )
        },
        default_factory=lambda: [None] * 16,
    )


@dataclass(slots=True)
class VenusSystemData:
    """System values from command 0x0D."""

    system_status: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x00, "<B")},
    )
    system_value_1: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x01, "<H")},
    )
    system_value_2: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x03, "<H")},
    )
    system_value_3: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x05, "<H")},
    )
    system_value_4: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x07, "<H")},
    )
    system_value_5: int | None = source_field(
        sources={_SYSTEM: FieldSource(0x09, "<H")},
    )


@dataclass(slots=True)
class VenusTimerData:
    """Adaptive-mode and smart-meter values from command 0x13."""

    adaptive_mode_enabled: bool | None = source_field(
        sources={_TIMER: FieldSource(0x00, "<B", nonzero)},
    )
    smart_meter_connected: bool | None = source_field(
        sources={_TIMER: FieldSource(0x25, "<B", nonzero)},
    )
    adaptive_power_out: float | None = source_field(
        sources={_TIMER: FieldSource(0x26, "<H", float)},
    )


@dataclass(slots=True)
class VenusConfigurationData:
    """Configuration readback values from commands 0x1A and 0x22."""

    config_mode: int | None = source_field(
        sources={_CONFIGURATION: FieldSource(0x00, "<B")},
    )
    config_status: int | None = source_field(
        sources={_CONFIGURATION: FieldSource(0x04, "<b")},
    )
    config_value: int | None = source_field(
        sources={_CONFIGURATION: FieldSource(0x10, "<B")},
    )
    ct_polling_rate: int | None = source_field(
        sources={_CT_POLLING_RATE: FieldSource(0x00, "<B")},
    )


@dataclass(slots=True)
class VenusDeviceInformation:
    """Variable-length identity values not yet handled by the binary schema."""

    device_type: str | None = None
    device_id: str | None = None
    serial_number: str | None = None
    mac_address: str | None = None
    firmware_version: str | None = None
    hardware_version: str | None = None


@dataclass(slots=True)
class VenusNetworkData:
    """Variable-length network values not yet handled by the binary schema."""

    wifi_ssid: str | None = None
    meter_ip: str | None = None
    network_info: str | None = None
    ip_address: str | None = None
    gateway: str | None = None
    subnet_mask: str | None = None
    dns_server: str | None = None
    local_api_status: str | None = None


@dataclass(slots=True)
class VenusData:
    """Cumulative data snapshot for one Venus-series device."""

    runtime: VenusRuntimeData = section_field(VenusRuntimeData)
    battery: VenusBatteryData = section_field(VenusBatteryData)
    system: VenusSystemData = section_field(VenusSystemData)
    timer: VenusTimerData = section_field(VenusTimerData)
    configuration: VenusConfigurationData = section_field(VenusConfigurationData)
    device: VenusDeviceInformation = field(default_factory=VenusDeviceInformation)
    network: VenusNetworkData = field(default_factory=VenusNetworkData)
