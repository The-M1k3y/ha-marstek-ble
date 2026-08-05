"""Unit tests for the original Marstek BLE frame and payload parser."""
from __future__ import annotations

import struct

import pytest

from custom_components.marstek_ble.marstek_device import MarstekData, MarstekProtocol


def frame(command: int, payload: bytes = b"") -> bytes:
    return MarstekProtocol.build_command(command, payload)


def test_build_command_sets_length_and_xor_checksum() -> None:
    packet = frame(0x22, b"\x01\x02")
    assert packet[:4] == bytes((0x73, 7, 0x23, 0x22))
    assert packet[4:-1] == b"\x01\x02"
    checksum = 0
    for value in packet[:-1]:
        checksum ^= value
    assert packet[-1] == checksum


@pytest.mark.parametrize(
    "packet",
    [
        b"",
        b"\x73\x05\x23\x03",
        b"\x72\x05\x23\x03\x00",
        b"\x73\x05\x22\x03\x00",
    ],
)
def test_parse_notification_rejects_short_or_invalid_headers(packet: bytes) -> None:
    assert MarstekProtocol.parse_notification(packet, MarstekData()) is False


def test_parse_notification_rejects_bad_checksum() -> None:
    packet = bytearray(frame(0x22, b"\x05"))
    packet[-1] ^= 0xFF
    assert MarstekProtocol.parse_notification(bytes(packet), MarstekData()) is False


def test_unhandled_command_is_rejected_without_mutating_data() -> None:
    data = MarstekData()
    assert MarstekProtocol.parse_notification(frame(0x7F, b"\x01"), data) is False
    assert data.field_updates == {}


def test_short_runtime_packet_parses_available_fields() -> None:
    payload = bytearray(37)
    payload[15] = 0b11
    payload[16] = 1
    payload[20:22] = struct.pack("<H", 777)
    payload[28] = 1
    data = MarstekData()

    assert MarstekProtocol.parse_notification(frame(0x03, payload), data) is True
    assert data.wifi_connected is True
    assert data.mqtt_connected is True
    assert data.out1_active is True
    assert data.out1_power == 777.0
    assert data.extern1_connected is True
    assert set(data.field_updates) == {
        "wifi_connected",
        "mqtt_connected",
        "out1_active",
        "out1_power",
        "extern1_connected",
    }


def test_long_runtime_packet_parses_plausible_values() -> None:
    payload = bytearray(100)
    payload[0:2] = struct.pack("<h", -120)
    payload[2:4] = struct.pack("<h", 340)
    payload[4] = 2
    payload[12:14] = struct.pack("<H", 154)
    payload[14:18] = struct.pack("<I", 1234)
    payload[18:22] = struct.pack("<I", 5678)
    payload[22:26] = struct.pack("<I", 345)
    payload[26:30] = struct.pack("<I", 678)
    payload[15] |= 0b11
    payload[16] = 1
    payload[20:22] = struct.pack("<H", 800)
    payload[28] = 1
    payload[33:35] = struct.pack("<h", -55)
    payload[35:37] = struct.pack("<h", 421)
    payload[41:45] = struct.pack("<I", 5151)
    payload[45:49] = struct.pack("<I", 4107)
    payload[74:76] = struct.pack("<H", 800)
    data = MarstekData()

    assert MarstekProtocol.parse_notification(frame(0x03, payload), data) is True
    assert data.grid_power == -120.0
    assert data.solar_power == 340.0
    assert data.work_mode == 2
    assert data.product_code == 154
    assert data.out1_power == 800.0
    assert data.temp_low == -5.5
    assert data.temp_high == 42.1
    assert data.total_energy_charged == 51.51
    assert data.total_energy_discharged == 41.07
    assert data.power_rating == 800


def test_device_info_packet_parses_known_keys_and_ignores_unknown_keys() -> None:
    payload = (
        b"type=HMG-50,id=device-1,sn=serial-1,mac=AA:BB:CC:DD:EE:FF,"
        b"dev_ver=202409090159,hw=3,other=ignored"
    )
    data = MarstekData()

    assert MarstekProtocol.parse_notification(frame(0x04, payload), data) is True
    assert data.device_type == "HMG-50"
    assert data.device_id == "device-1"
    assert data.serial_number == "serial-1"
    assert data.mac_address == "AA:BB:CC:DD:EE:FF"
    assert data.firmware_version == "202409090159"
    assert data.hardware_version == "3"


def test_wifi_system_timer_config_and_scalar_packets() -> None:
    data = MarstekData()
    system = bytes((7,)) + struct.pack("<HHHHH", 11, 22, 33, 44, 55)
    timer = bytearray(45)
    timer[0] = 1
    timer[37] = 1
    timer[38:40] = struct.pack("<H", 650)
    config = bytearray(17)
    config[0] = 2
    config[4:5] = struct.pack("<b", -3)
    config[16] = 9

    assert MarstekProtocol.parse_notification(frame(0x08, b" Test WiFi "), data)
    assert MarstekProtocol.parse_notification(frame(0x0D, system), data)
    assert MarstekProtocol.parse_notification(frame(0x13, timer), data)
    assert MarstekProtocol.parse_notification(frame(0x1A, config), data)
    assert MarstekProtocol.parse_notification(frame(0x22, b"\x77"), data)
    assert MarstekProtocol.parse_notification(frame(0x28, b"\x01\x90\x1f"), data)

    assert data.wifi_ssid == "Test WiFi"
    assert (data.system_status, data.system_value_5) == (7, 55)
    assert data.adaptive_mode_enabled is True
    assert data.smart_meter_connected is True
    assert data.adaptive_power_out == 650.0
    assert (data.config_mode, data.config_status, data.config_value) == (2, -3, 9)
    assert data.ct_polling_rate == 0x77
    assert data.local_api_status == "enabled/8080"


def test_bms_packet_parses_limits_state_runtime_and_all_cells() -> None:
    payload = bytearray(80)
    payload[0:2] = struct.pack("<H", 215)
    payload[2:4] = struct.pack("<H", 571)
    payload[4:6] = struct.pack("<H", 500)
    payload[6:8] = struct.pack("<h", 900)
    payload[8:10] = struct.pack("<H", 82)
    payload[10:12] = struct.pack("<H", 99)
    payload[12:14] = struct.pack("<H", 5120)
    payload[14:16] = struct.pack("<H", 5037)
    payload[16:18] = struct.pack("<h", -123)
    payload[18:20] = struct.pack("<H", 24)
    payload[26:28] = struct.pack("<H", 7)
    payload[28:32] = struct.pack("<I", 0x12345678)
    payload[32:36] = struct.pack("<I", 7_200_000)
    payload[38:48] = struct.pack("<HHHHH", 31, 21, 22, 23, 24)
    for index in range(16):
        payload[48 + index * 2 : 50 + index * 2] = struct.pack("<H", 3140 + index)
    data = MarstekData()

    assert MarstekProtocol.parse_notification(frame(0x14, payload), data) is True
    assert data.bms_version == 215
    assert data.voltage_limit == 57.1
    assert data.charge_current_limit == 50.0
    assert data.discharge_current_limit == 90.0
    assert data.battery_soc == 82.0
    assert data.battery_soh == 99.0
    assert data.design_capacity == 5120.0
    assert data.battery_voltage == 50.37
    assert data.battery_current == -12.3
    assert data.runtime_hours == 2.0
    assert data.cell_voltages == pytest.approx(
        [3.140 + index / 1000 for index in range(16)]
    )


def test_network_and_meter_ip_packets() -> None:
    data = MarstekData()
    network = b"ip:192.0.2.10,gate:192.0.2.1,mask:255.255.255.0,dns:192.0.2.53"
    assert MarstekProtocol.parse_notification(frame(0x24, network), data)
    assert MarstekProtocol.parse_notification(frame(0x21, b"192.0.2.20\x00"), data)
    assert data.network_info == network.decode()
    assert data.ip_address == "192.0.2.10"
    assert data.gateway == "192.0.2.1"
    assert data.subnet_mask == "255.255.255.0"
    assert data.dns_server == "192.0.2.53"
    assert data.meter_ip == "192.0.2.20"


def test_payload_minimum_lengths_are_enforced() -> None:
    lengths = {
        0x03: 36,
        0x0D: 10,
        0x13: 44,
        0x14: 79,
        0x1A: 16,
        0x22: 0,
        0x28: 2,
    }
    for command, length in lengths.items():
        assert (
            MarstekProtocol.parse_notification(
                frame(command, bytes(length)), MarstekData()
            )
            is False
        )


def test_field_metadata_contains_source_timestamp_age_and_payload(monkeypatch) -> None:
    data = MarstekData()
    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.time.time", lambda: 110.0
    )
    data.mark_field_update(
        "battery_soc", 0x14, timestamp=100.0, payload=b"\x01\x02"
    )
    assert data.get_field_metadata("missing") is None
    assert data.get_field_metadata("battery_soc") == {
        "command": 0x14,
        "command_hex": "0x14",
        "timestamp": "1970-01-01T00:01:40+00:00",
        "age_seconds": 10.0,
        "payload_hex": "0102",
    }


@pytest.mark.known_issue
def test_notification_length_byte_must_match_actual_frame_length() -> None:
    packet = bytearray(frame(0x22, b"\x05"))
    packet[1] += 1
    checksum = 0
    for value in packet[:-1]:
        checksum ^= value
    packet[-1] = checksum
    assert MarstekProtocol.parse_notification(bytes(packet), MarstekData()) is False


@pytest.mark.known_issue
def test_timestamp_zero_is_preserved_in_field_metadata(monkeypatch) -> None:
    data = MarstekData()
    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.time.time", lambda: 50.0
    )
    data.mark_field_update("battery_soc", 0x14, timestamp=0.0)
    metadata = data.get_field_metadata("battery_soc")
    assert metadata is not None
    assert metadata["timestamp"] == "1970-01-01T00:00:00+00:00"
    assert metadata["age_seconds"] == 50.0


@pytest.mark.known_issue
def test_empty_device_info_payload_is_rejected() -> None:
    assert MarstekProtocol.parse_notification(frame(0x04, b""), MarstekData()) is False


@pytest.mark.known_issue
def test_empty_meter_ip_payload_is_rejected() -> None:
    assert MarstekProtocol.parse_notification(frame(0x21, b""), MarstekData()) is False
