"""Tests for the Jupiter-C Plus product runtime."""

from __future__ import annotations

import struct

import pytest

from custom_components.marstek_ble.entity import EntityPlatform
from custom_components.marstek_ble.product_runtime import ProductProtocol
from custom_components.marstek_ble.products import JUPITER_RUNTIME, runtime_for_id, runtime_for_name
from custom_components.marstek_ble.products.jupiter_runtime import RuntimeJupiterData


def frame(command: int, payload: bytes = b"") -> bytes:
    """Build a valid Marstek protocol frame."""

    return ProductProtocol.build_command(command, payload)


def test_jupiter_runtime_is_registered_for_product_id_and_discovery_name() -> None:
    assert runtime_for_id("jupiter_c_plus") is JUPITER_RUNTIME
    assert runtime_for_name("MST_JPLS_TEST") is JUPITER_RUNTIME
    assert JUPITER_RUNTIME.matches_name("MST_JPLS_") is True
    assert JUPITER_RUNTIME.matches_name("MST_ACCP_TEST") is False


def test_jupiter_poll_schedule_uses_only_observed_response_commands() -> None:
    fast = [command.command for command in JUPITER_RUNTIME.fast_poll]
    medium = [command.command for command in JUPITER_RUNTIME.medium_poll]

    assert fast == [0x03, 0x14]
    assert medium == [0x0D, 0x08, 0x22, 0x21, 0x24, 0x04, 0x13]
    assert JUPITER_RUNTIME.medium_poll[3].payload == b"\x0b"
    assert 0x1A not in fast + medium
    assert 0x1C not in fast + medium


def test_jupiter_runtime_summary_parses_pv_power_and_system_values() -> None:
    data = JUPITER_RUNTIME.create_data()
    assert isinstance(data, RuntimeJupiterData)

    payload = bytearray(74)
    payload[0:2] = struct.pack("<H", 123)
    payload[2] = 1
    payload[3:5] = struct.pack("<H", 234)
    payload[5] = 1
    payload[6:8] = struct.pack("<H", 345)
    payload[8] = 0
    payload[9:11] = struct.pack("<H", 456)
    payload[11] = 1
    payload[12:14] = struct.pack("<H", 640)
    payload[14] = 1
    payload[18] = 1
    payload[19:21] = struct.pack("<H", 250)
    payload[21] = 73
    payload[23:27] = struct.pack("<I", 1234)
    payload[27:31] = struct.pack("<I", 5678)
    payload[31:35] = struct.pack("<I", 9012)
    payload[39:43] = struct.pack("<I", 345)
    payload[43:47] = struct.pack("<I", 678)
    payload[47:49] = struct.pack("<H", 101)
    payload[49:51] = struct.pack("<H", 202)
    payload[51:53] = struct.pack("<H", 303)
    payload[53:55] = struct.pack("<H", 404)
    payload[60] = 5

    paths = JUPITER_RUNTIME.parse_payload(0x03, bytes(payload), data)

    assert paths is not None
    assert data.pv_inputs[0].power == 123.0
    assert data.pv_inputs[0].connected is True
    assert data.pv_inputs[2].connected is False
    assert data.pv_inputs[3].power == 456.0
    assert data.runtime.ac_output_power == 640.0
    assert data.runtime.ac_output_active is True
    assert data.runtime.battery_charging_active is True
    assert data.runtime.stored_battery_energy == 2500.0
    assert data.runtime.battery_soc == 73.0
    assert data.energy.daily_pv_generation == pytest.approx(12.34)
    assert data.energy.monthly_pv_generation == pytest.approx(56.78)
    assert data.energy.total_pv_generation == pytest.approx(90.12)
    assert data.energy.daily_discharge_energy == pytest.approx(3.45)
    assert data.energy.monthly_discharge_energy == pytest.approx(6.78)
    assert data.runtime.ems_firmware_version == 101
    assert data.runtime.inverter_firmware_version == 202
    assert data.runtime.mppt_firmware_version == 303
    assert data.runtime.bms_firmware_version == 404
    assert data.runtime.operational_status == 5

    # Temporary compatibility reads keep the current sensor platform functional.
    assert data.grid_power == 640.0
    assert data.solar_power == 1158.0
    assert data.battery_soc == 73.0
    assert data.out1_active is True


def test_jupiter_detailed_telemetry_parses_signed_battery_and_pack_records() -> None:
    data = JUPITER_RUNTIME.create_data()
    payload = bytearray(166)

    payload[6:8] = struct.pack("<H", 2305)
    payload[12:14] = struct.pack("<H", 5000)
    payload[16:18] = struct.pack("<h", 615)
    payload[18:20] = struct.pack("<h", 37)
    payload[40:42] = struct.pack("<H", 425)
    payload[42:44] = struct.pack("<H", 81)
    payload[44:46] = struct.pack("<H", 344)
    payload[88:90] = struct.pack("<H", 584)
    payload[90:92] = struct.pack("<H", 250)
    payload[92:94] = struct.pack("<H", 300)
    payload[94:96] = struct.pack("<H", 68)
    payload[96:98] = struct.pack("<H", 97)
    payload[98:100] = struct.pack("<H", 7680)
    payload[102:104] = struct.pack("<H", 5123)
    payload[104:106] = struct.pack("<h", -123)
    payload[106:108] = struct.pack("<h", 245)
    payload[118:120] = struct.pack("<H", 2)
    payload[120:122] = struct.pack("<H", 4321)

    payload[122] = 7
    payload[123] = 3
    payload[124:126] = struct.pack("<H", 3345)
    payload[126:128] = struct.pack("<H", 3298)
    payload[128:130] = struct.pack("<H", 1)

    payload[130] = 8
    payload[131] = 2
    payload[132:134] = struct.pack("<H", 3350)
    payload[134:136] = struct.pack("<H", 3301)
    payload[136:138] = struct.pack("<H", 2)

    paths = JUPITER_RUNTIME.parse_payload(0x14, bytes(payload), data)

    assert paths is not None
    assert data.inverter.grid_voltage == pytest.approx(230.5)
    assert data.inverter.grid_frequency == pytest.approx(50.0)
    assert data.runtime.ac_output_power == 615.0
    assert data.inverter.temperature == 37.0
    assert data.pv_inputs[0].voltage == pytest.approx(42.5)
    assert data.pv_inputs[0].current == pytest.approx(8.1)
    assert data.pv_inputs[0].power == pytest.approx(34.4)
    assert data.battery.charge_voltage_limit == pytest.approx(58.4)
    assert data.battery.charge_current_limit == pytest.approx(25.0)
    assert data.battery.discharge_current_limit == pytest.approx(30.0)
    assert data.runtime.battery_soc == 68.0
    assert data.battery.soh == 97.0
    assert data.battery.rated_capacity == 7680.0
    assert data.battery.voltage == pytest.approx(51.23)
    assert data.battery.current == pytest.approx(-12.3)
    assert data.battery.temperature == pytest.approx(24.5)
    assert data.battery.pack_count == 2
    assert data.runtime.stored_battery_energy == 4321.0
    assert data.battery.packs[0].highest_cell_index == 7
    assert data.battery.packs[0].highest_cell_voltage == pytest.approx(3.345)
    assert data.battery.packs[0].lowest_cell_voltage == pytest.approx(3.298)
    assert data.battery.packs[1].status == 2

    assert data.battery_voltage == pytest.approx(51.23)
    assert data.battery_current == pytest.approx(-12.3)
    assert data.design_capacity == 7680.0
    assert data.remaining_capacity == pytest.approx(5222.4)
    assert data.available_capacity == pytest.approx(2457.6)


def test_jupiter_device_information_and_wifi_parsers_ignore_unknown_or_bad_values() -> None:
    data = JUPITER_RUNTIME.create_data()

    paths = JUPITER_RUNTIME.parse_payload(
        0x04,
        b"type=JPLS,id=device,mac=00:11:22:33:44:55,ems_v=101,inv_v=bad,unknown=x",
        data,
    )
    assert paths is not None
    assert data.identity.device_type == "JPLS"
    assert data.identity.device_id == "device"
    assert data.identity.mac_address == "00:11:22:33:44:55"
    assert data.runtime.ems_firmware_version == 101
    assert data.runtime.inverter_firmware_version is None

    assert JUPITER_RUNTIME.parse_payload(0x08, b"Test WiFi\x00", data)
    assert data.identity.wifi_ssid == "Test WiFi"
    assert JUPITER_RUNTIME.parse_payload(0x08, b"\xff", data) == ()


def test_jupiter_protocol_tracks_canonical_and_legacy_metadata(monkeypatch) -> None:
    data = JUPITER_RUNTIME.create_data()
    protocol = ProductProtocol(JUPITER_RUNTIME)
    monkeypatch.setattr(
        "custom_components.marstek_ble.product_runtime.time.time",
        lambda: 200.0,
    )

    payload = bytearray(166)
    payload[102:104] = struct.pack("<H", 5050)
    payload[104:106] = struct.pack("<h", 100)

    assert protocol.parse_notification(frame(0x14, payload), data) is True
    assert data.battery_voltage == pytest.approx(50.5)
    assert data.battery_current == pytest.approx(10.0)

    canonical = data.get_field_metadata(("battery", "voltage"))
    legacy = data.get_field_metadata("battery_voltage")
    assert canonical is not None
    assert canonical["command_hex"] == "0x14"
    assert legacy == canonical


def test_jupiter_event_history_is_twenty_fixed_records() -> None:
    data = JUPITER_RUNTIME.create_data()
    payload = bytearray(160)
    payload[0:2] = struct.pack("<H", 2026)
    payload[2:8] = bytes((8, 9, 12, 34, 5, 1))
    payload[8:10] = struct.pack("<H", 2025)
    payload[10:16] = bytes((12, 31, 23, 59, 9, 0))

    assert JUPITER_RUNTIME.parse_payload(0x13, bytes(payload), data)
    assert len(data.events) == 20
    assert data.events[0].year == 2026
    assert data.events[0].month == 8
    assert data.events[0].event_value == 5
    assert data.events[0].event_state == 1
    assert data.events[1].year == 2025
    assert data.events[1].event_value == 9


def test_jupiter_runtime_summary_decodes_battery_state_values() -> None:
    expected = (
        (0, "idle", False),
        (1, "charging", True),
        (2, "discharging", False),
        (255, "unknown", None),
    )

    for raw_value, state, charging_active in expected:
        data = JUPITER_RUNTIME.create_data()
        payload = bytearray(74)
        payload[18] = raw_value

        assert JUPITER_RUNTIME.parse_payload(0x03, bytes(payload), data)
        assert data.runtime.battery_state == state
        assert data.runtime.battery_charging_active is charging_active


def test_jupiter_entity_plan_uses_verified_state_and_display_metadata() -> None:
    data = JUPITER_RUNTIME.create_data()
    plan = JUPITER_RUNTIME.profile.build_entity_plan(data)
    sensors = {
        item.unique_key: item
        for item in plan.entities
        if item.platform is EntityPlatform.SENSOR
    }
    binary_sensors = {
        item.unique_key: item
        for item in plan.entities
        if item.platform is EntityPlatform.BINARY_SENSOR
    }

    assert sensors["battery_state"].description.name == "Battery State"
    assert "grid_current" not in sensors
    assert sensors["grid_frequency"].description.suggested_display_precision == 2
    assert sensors["mac_address"].description.name == "Bluetooth MAC Address"
    assert "battery_charging_active" not in binary_sensors
    assert "battery_charging" not in binary_sensors
