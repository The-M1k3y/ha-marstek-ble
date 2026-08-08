"""Drop-in compatibility tests for the runtime-enabled Venus data model."""
from __future__ import annotations

import struct
from dataclasses import fields
from types import SimpleNamespace
from typing import Any

import pytest

from bleak.backends.device import BLEDevice

from custom_components.marstek_ble import binary_sensor, button, select, sensor, switch
from custom_components.marstek_ble.marstek_device import MarstekData, MarstekProtocol
from custom_components.marstek_ble.product_runtime import ProductProtocol
from custom_components.marstek_ble.products import VENUS_RUNTIME, VenusData


ENTRY_ID = "entry-1"
ADDRESS = "AA:BB:CC:DD:EE:FF"
DEVICE_NAME = "Battery"


def _long_runtime_payload() -> bytes:
    payload = bytearray(109)
    struct.pack_into("<h", payload, 0x00, -350)
    struct.pack_into("<h", payload, 0x02, 825)
    payload[0x04] = 3
    struct.pack_into("<H", payload, 0x0C, 0x1234)
    struct.pack_into("<I", payload, 0x0E, 1_234)
    struct.pack_into("<I", payload, 0x12, 12_345)
    struct.pack_into("<I", payload, 0x16, 876)
    struct.pack_into("<I", payload, 0x1A, 3_456)
    struct.pack_into("<h", payload, 0x21, 215)
    struct.pack_into("<h", payload, 0x23, 312)
    struct.pack_into("<I", payload, 0x29, 34_567)
    struct.pack_into("<I", payload, 0x2D, 23_456)
    struct.pack_into("<H", payload, 0x4A, 2_500)
    return bytes(payload)


def _short_runtime_payload() -> bytes:
    payload = bytearray(37)
    payload[0x0F] = 0b11
    payload[0x10] = 1
    struct.pack_into("<H", payload, 0x14, 777)
    payload[0x1C] = 1
    return bytes(payload)


def _system_payload() -> bytes:
    payload = bytearray(11)
    payload[0] = 2
    for index, value in enumerate((101, 202, 303, 404, 505)):
        struct.pack_into("<H", payload, 1 + index * 2, value)
    return bytes(payload)


def _timer_payload() -> bytes:
    payload = bytearray(45)
    payload[0] = 1
    payload[37] = 1
    struct.pack_into("<H", payload, 38, 450)
    return bytes(payload)


def _bms_payload() -> bytes:
    payload = bytearray(80)
    struct.pack_into("<H", payload, 0x00, 220)
    struct.pack_into("<H", payload, 0x02, 584)
    struct.pack_into("<H", payload, 0x04, 500)
    struct.pack_into("<h", payload, 0x06, 900)
    struct.pack_into("<H", payload, 0x08, 76)
    struct.pack_into("<H", payload, 0x0A, 98)
    struct.pack_into("<H", payload, 0x0C, 5_120)
    struct.pack_into("<H", payload, 0x0E, 5_124)
    struct.pack_into("<h", payload, 0x10, -85)
    struct.pack_into("<H", payload, 0x12, 25)
    struct.pack_into("<H", payload, 0x1A, 3)
    struct.pack_into("<I", payload, 0x1C, 0x10203040)
    struct.pack_into("<I", payload, 0x20, 123 * 3_600_000)
    struct.pack_into("<H", payload, 0x26, 29)
    for index, value in enumerate((24, 25, 26, 27)):
        struct.pack_into("<H", payload, 0x28 + index * 2, value)
    for index in range(16):
        struct.pack_into("<H", payload, 0x30 + index * 2, 3_200 + index)
    return bytes(payload)


def _config_payload() -> bytes:
    payload = bytearray(17)
    payload[0] = 2
    struct.pack_into("<b", payload, 4, -1)
    payload[16] = 7
    return bytes(payload)


SYNTHETIC_PACKETS: tuple[tuple[int, bytes], ...] = (
    (0x03, _long_runtime_payload()),
    (0x03, _short_runtime_payload()),
    (
        0x04,
        b"type=HMG-50,id=synthetic-device,sn=SYNTHETIC-0002,"
        b"mac=02:00:00:00:00:02,dev_ver=202608080001,hw=3",
    ),
    (0x08, b"Synthetic WiFi"),
    (0x0D, _system_payload()),
    (0x13, _timer_payload()),
    (0x14, _bms_payload()),
    (0x1A, _config_payload()),
    (0x21, b"192.0.2.20\x00"),
    (0x22, b"\x01"),
    (
        0x24,
        b"ip:192.0.2.10,gate:192.0.2.1,"
        b"mask:255.255.255.0,dns:192.0.2.53",
    ),
    (0x28, b"\x01\x90\x1f"),
    (0x1C, b"synthetic-unparsed-log"),
)

LEGACY_FIELDS = tuple(
    field.name for field in fields(MarstekData) if field.name != "field_updates"
)


def _assert_legacy_value_equal(actual: Any, expected: Any) -> None:
    if isinstance(expected, float):
        assert actual == pytest.approx(expected)
    elif isinstance(expected, list):
        assert isinstance(actual, list)
        assert len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected, strict=True):
            _assert_legacy_value_equal(actual_item, expected_item)
    else:
        assert actual == expected


def _parse_synthetic_snapshots() -> tuple[MarstekData, VenusData]:
    legacy = MarstekData()
    venus = VenusData()
    product_protocol = ProductProtocol(VENUS_RUNTIME)

    for command, payload in SYNTHETIC_PACKETS:
        frame = MarstekProtocol.build_command(command, payload)
        assert ProductProtocol.build_command(command, payload) == frame
        legacy_result = MarstekProtocol.parse_notification(frame, legacy)
        product_result = product_protocol.parse_notification(frame, venus)
        assert product_result is legacy_result

    return legacy, venus


def test_product_runtime_matches_legacy_flat_state_after_every_synthetic_packet(
) -> None:
    legacy = MarstekData()
    venus = VenusData()
    product_protocol = ProductProtocol(VENUS_RUNTIME)

    for command, payload in SYNTHETIC_PACKETS:
        frame = MarstekProtocol.build_command(command, payload)
        legacy_result = MarstekProtocol.parse_notification(frame, legacy)
        product_result = product_protocol.parse_notification(frame, venus)

        assert product_result is legacy_result, f"command 0x{command:02X}"
        for field_name in LEGACY_FIELDS:
            _assert_legacy_value_equal(
                getattr(venus, field_name),
                getattr(legacy, field_name),
            )


class _FakeDevice:
    async def send_command(self, command: int, payload: bytes = b"") -> bool:
        return True


def _coordinator(data: MarstekData | VenusData) -> SimpleNamespace:
    ble_device = BLEDevice(ADDRESS, "MST_ACCP_SYNTHETIC")
    return SimpleNamespace(
        data=data,
        ble_device=ble_device,
        device_name=DEVICE_NAME,
        address=ADDRESS,
        last_update_success=True,
        device=_FakeDevice(),
    )


def _entry(coordinator: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(entry_id=ENTRY_ID, runtime_data=coordinator)


async def _entities_for(data: MarstekData | VenusData) -> dict[str, list[Any]]:
    coordinator = _coordinator(data)
    entry = _entry(coordinator)
    created: dict[str, list[Any]] = {}
    for platform, module in (
        ("sensor", sensor),
        ("binary_sensor", binary_sensor),
        ("button", button),
        ("switch", switch),
        ("select", select),
    ):
        entities: list[Any] = []
        await module.async_setup_entry(None, entry, entities.extend)
        created[platform] = entities
    return created


def _contract(platform: str, entity: Any) -> dict[str, Any]:
    options = getattr(entity, "_attr_options", None)
    return {
        "platform": platform,
        "unique_id": entity._attr_unique_id,
        "name": entity._attr_name,
        "unit": getattr(entity, "_attr_native_unit_of_measurement", None),
        "device_class": getattr(entity, "_attr_device_class", None),
        "options": tuple(options) if options is not None else None,
        "device_info": entity.device_info,
    }


def _state(platform: str, entity: Any) -> Any:
    if platform == "sensor":
        return entity.native_value
    if platform == "binary_sensor":
        return entity.is_on
    if platform == "switch":
        return (entity.is_on, entity.assumed_state)
    if platform == "select":
        return entity.current_option
    return None


# Snapshot of the main-branch HA entity contract. The CT polling-rate select
# unique-id change is the one explicitly accepted migration exception below.
SENSOR_SPECS = (
    ("battery_voltage", "Battery Voltage", "V", "voltage"),
    ("battery_current", "Battery Current", "A", "current"),
    ("battery_soc", "Battery SOC", "%", "battery"),
    ("battery_soh", "Battery SOH", "%", None),
    ("battery_temp", "Battery Temperature", "°C", "temperature"),
    ("battery_power", "Battery Power", "W", "power"),
    ("grid_power", "Grid Power", "W", "power"),
    ("solar_power", "Solar Power", "W", "power"),
    ("battery_power_in", "Battery Power In", "W", "power"),
    ("battery_power_out", "Battery Power Out", "W", "power"),
    ("out1_power", "Output 1 Power", "W", "power"),
    ("daily_energy_charged", "Daily Energy Charged", "kWh", "energy"),
    ("daily_energy_discharged", "Daily Energy Discharged", "kWh", "energy"),
    ("monthly_energy_charged", "Monthly Energy Charged", "kWh", "energy"),
    ("monthly_energy_discharged", "Monthly Energy Discharged", "kWh", "energy"),
    ("total_energy_charged", "Total Energy Charged", "kWh", "energy"),
    ("total_energy_discharged", "Total Energy Discharged", "kWh", "energy"),
    ("design_capacity", "Design Capacity", "Wh", "energy"),
    ("remaining_capacity", "Remaining Capacity", "Wh", "energy_storage"),
    ("available_capacity", "Available Capacity", "Wh", "energy_storage"),
    ("temp_low", "Temperature Low", "°C", "temperature"),
    ("temp_high", "Temperature High", "°C", "temperature"),
    ("mosfet_temp", "MOSFET Temperature", "°C", "temperature"),
    ("temp_sensor_1", "Temperature Sensor 1", "°C", "temperature"),
    ("temp_sensor_2", "Temperature Sensor 2", "°C", "temperature"),
    ("temp_sensor_3", "Temperature Sensor 3", "°C", "temperature"),
    ("temp_sensor_4", "Temperature Sensor 4", "°C", "temperature"),
    ("system_status", "System Status", None, None),
    ("config_mode", "Config Mode", None, None),
    ("ct_polling_rate", "CT Polling Rate", None, None),
    ("work_mode", "Work Mode", None, None),
    ("product_code", "Product Code", None, None),
    ("power_rating", "Power Rating", "W", "power"),
    ("bms_version", "BMS Version", None, None),
    ("voltage_limit", "Voltage Limit", "V", "voltage"),
    ("charge_current_limit", "Charge Current Limit", "A", "current"),
    ("discharge_current_limit", "Discharge Current Limit", "A", "current"),
    ("error_code", "Error Code", None, None),
    ("warning_code", "Warning Code", None, None),
    ("runtime_hours", "Runtime", "h", "duration"),
) + tuple(
    (f"cell_{index}_voltage", f"Cell {index} Voltage", "V", "voltage")
    for index in range(1, 17)
) + (
    ("battery_state", "Battery State", None, None),
    ("device_type", "Device Type", None, None),
    ("device_id", "Device ID", None, None),
    ("serial_number", "Serial Number", None, None),
    ("mac_address", "MAC Address", None, None),
    ("firmware_version", "Firmware Version", None, None),
    ("hardware_version", "Hardware Version", None, None),
    ("wifi_ssid", "WiFi SSID", None, None),
    ("network_info", "Network Info", None, None),
    ("ip_address", "IP Address", None, None),
    ("gateway", "Gateway", None, None),
    ("subnet_mask", "Subnet Mask", None, None),
    ("dns_server", "DNS Server", None, None),
    ("meter_ip", "Meter IP", None, None),
)

BINARY_SENSOR_SPECS = (
    ("wifi_connected", "WiFi Connected", "connectivity"),
    ("mqtt_connected", "MQTT Connected", "connectivity"),
    ("out1_active", "Output 1 Active", "power"),
    ("extern1_connected", "External 1 Connected", "connectivity"),
    ("smart_meter_connected", "Smart Meter Connected", "connectivity"),
)

BUTTON_SPECS = (
    ("reboot", "Reboot"),
    ("set_800w_mode", "Set 800W Mode"),
    ("set_2500w_mode", "Set 2500W Mode"),
    ("set_ac_power_2500w", "Set AC Power 2500W"),
    ("set_total_power_2500w", "Set Total Power 2500W"),
)

SWITCH_SPECS = (
    ("out1_control", "Output 1 Control"),
    ("eps_mode", "EPS Mode"),
    ("ac_input", "AC Input"),
    ("generator", "Generator"),
    ("buzzer", "Buzzer"),
)

# The CT polling-rate select intentionally uses its migration-branch unique-id key.
SELECT_SPECS = (
    ("operating_mode", "Operating Mode", ("Self-Consumption", "Manual")),
    (
        "charge_mode",
        "Charge Mode",
        ("Load First", "PV2 Passthrough", "Simultaneous Charge Discharge"),
    ),
    (
        "ct_polling_rate_select",
        "CT Polling Rate",
        ("Fastest (0)", "Medium (1)", "Slowest (2)"),
    ),
)


def _expected_contract() -> list[dict[str, Any]]:
    device_info = {
        "identifiers": {("marstek_ble", ADDRESS)},
        "connections": {("bluetooth", ADDRESS)},
        "name": DEVICE_NAME,
        "manufacturer": "Marstek",
        "model": "Venus E",
    }
    expected: list[dict[str, Any]] = []

    for key, name, unit, device_class in SENSOR_SPECS:
        expected.append(
            {
                "platform": "sensor",
                "unique_id": f"{ENTRY_ID}_{key}",
                "name": name,
                "unit": unit,
                "device_class": device_class,
                "options": None,
                "device_info": device_info,
            }
        )
    for key, name, device_class in BINARY_SENSOR_SPECS:
        expected.append(
            {
                "platform": "binary_sensor",
                "unique_id": f"{ENTRY_ID}_{key}",
                "name": name,
                "unit": None,
                "device_class": device_class,
                "options": None,
                "device_info": device_info,
            }
        )
    for platform, specs in (("button", BUTTON_SPECS), ("switch", SWITCH_SPECS)):
        for key, name in specs:
            expected.append(
                {
                    "platform": platform,
                    "unique_id": f"{ENTRY_ID}_{key}",
                    "name": name,
                    "unit": None,
                    "device_class": None,
                    "options": None,
                    "device_info": device_info,
                }
            )
    for key, name, options in SELECT_SPECS:
        expected.append(
            {
                "platform": "select",
                "unique_id": f"{ENTRY_ID}_{key}",
                "name": name,
                "unit": None,
                "device_class": None,
                "options": options,
                "device_info": device_info,
            }
        )

    return sorted(expected, key=lambda item: (item["platform"], item["unique_id"]))


@pytest.mark.asyncio
async def test_venus_data_preserves_existing_home_assistant_entity_contract_and_state(
) -> None:
    legacy_data, venus_data = _parse_synthetic_snapshots()
    legacy_entities = await _entities_for(legacy_data)
    venus_entities = await _entities_for(venus_data)

    venus_contract = sorted(
        (
            _contract(platform, entity)
            for platform, entities in venus_entities.items()
            for entity in entities
        ),
        key=lambda item: (item["platform"], item["unique_id"]),
    )
    assert venus_contract == _expected_contract()

    legacy_by_id = {
        (platform, entity._attr_unique_id): entity
        for platform, entities in legacy_entities.items()
        for entity in entities
    }
    venus_by_id = {
        (platform, entity._attr_unique_id): entity
        for platform, entities in venus_entities.items()
        for entity in entities
    }
    assert venus_by_id.keys() == legacy_by_id.keys()

    for identity, venus_entity in venus_by_id.items():
        platform = identity[0]
        legacy_entity = legacy_by_id[identity]
        _assert_legacy_value_equal(
            _state(platform, venus_entity),
            _state(platform, legacy_entity),
        )
        assert venus_entity.available == legacy_entity.available
