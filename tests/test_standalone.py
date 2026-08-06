"""Unit tests for the original standalone ESPHome proxy utility."""
from __future__ import annotations

import asyncio
import struct
from collections import deque

import pytest

from aioesphomeapi.core import TimeoutAPIError
from aioesphomeapi.model import BluetoothLEAdvertisement

from standalone_test import marstek_basic_info as standalone


def test_frame_buffer_handles_noise_fragmentation_and_multiple_frames() -> None:
    first = standalone.create_command_frame(0x03, b"\x01")
    second = standalone.create_command_frame(0x04, b"abc")
    buffer = standalone.FrameBuffer()
    assert buffer.feed(b"junk" + first[:3]) == []
    assert buffer.feed(first[3:] + second) == [first, second]


def test_frame_buffer_recovers_from_spurious_start_byte_in_noise() -> None:
    packet = standalone.create_command_frame(0x03)
    buffer = standalone.FrameBuffer()
    assert buffer.feed(b"noise" + packet) == [packet]


def test_frame_buffer_drops_zero_length_prefix() -> None:
    packet = standalone.create_command_frame(0x22, b"\x02")
    buffer = standalone.FrameBuffer()
    assert buffer.feed(b"\x73\x00" + packet) == [packet]


@pytest.mark.parametrize(
    ("raw", "mac", "name"),
    [
        ("AA:BB:CC:DD:EE:FF", 0xAABBCCDDEEFF, None),
        ("aa-bb-cc-dd-ee-ff", 0xAABBCCDDEEFF, None),
        ("0xAABBCCDDEEFF", 0xAABBCCDDEEFF, None),
        (str(0xAABBCCDDEEFF), 0xAABBCCDDEEFF, None),
        ("mst_accp_test", None, "MST_ACCP_TEST"),
    ],
)
def test_target_spec_parses_supported_identifiers(raw, mac, name) -> None:
    target = standalone.TargetSpec.from_string(raw)
    assert target.mac_int == mac
    assert target.name_upper == name


def test_target_spec_rejects_blank_and_matches_address_or_name() -> None:
    with pytest.raises(ValueError, match="blank"):
        standalone.TargetSpec.from_string("   ")
    by_mac = standalone.TargetSpec.from_string("AA:BB:CC:DD:EE:FF")
    assert by_mac.matches_simple(0xAABBCCDDEEFF, "anything") is True
    assert by_mac.matches_simple(1, "anything") is False
    by_name = standalone.TargetSpec.from_string("MST_ACCP_TEST")
    advertisement = BluetoothLEAdvertisement(
        1, name=" mst_accp_test ", rssi=-50, service_uuids=[]
    )
    assert by_name.matches(advertisement) is True
    assert by_name.matches_simple(1, "other") is False


def test_resolved_device_formats_address_and_address_type() -> None:
    device = standalone.ResolvedDevice("test", 0xAABBCCDDEEFF, 1, -60, "test")
    assert device.address_human == "AA:BB:CC:DD:EE:FF"
    assert device.address_type_label == "random"
    device.address_type = 9
    assert device.address_type_label == "unknown(9)"


def test_create_and_parse_frame_round_trip() -> None:
    packet = standalone.create_command_frame(0x14, bytearray(b"\x01\x02"))
    assert packet[1] == len(packet)
    assert standalone.parse_frame(packet) == (0x14, b"\x01\x02")


def _replace_identifier(packet: bytes, identifier: int) -> bytes:
    result = bytearray(packet)
    result[2] = identifier
    checksum = 0
    for value in result[:-1]:
        checksum ^= value
    result[-1] = checksum
    return bytes(result)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda packet: b"\x73\x01", "too short"),
        (lambda packet: bytes((0x72,)) + packet[1:], "start byte"),
        (
            lambda packet: packet[:1]
            + bytes((packet[1] + 1,))
            + packet[2:],
            "Length mismatch",
        ),
        (
            lambda packet: packet[:-1] + bytes((packet[-1] ^ 0xFF,)),
            "Checksum mismatch",
        ),
        (lambda packet: _replace_identifier(packet, 0x22), "identifier"),
    ],
)
def test_parse_frame_rejects_malformed_frames(mutator, message) -> None:
    packet = standalone.create_command_frame(0x03)
    with pytest.raises(ValueError, match=message):
        standalone.parse_frame(mutator(packet))


def test_connection_error_to_text_handles_known_and_unknown_codes() -> None:
    assert standalone.connection_error_to_text(1) == "Timeout"
    assert standalone.connection_error_to_text(0x7F) == "0x7F"


def test_binary_read_helpers_and_timestamp_helpers() -> None:
    payload = b"\x01\x02\x80\xFFtext\x00"
    assert standalone._read_le(payload, 0, 2) == 0x0201
    assert standalone._read_le(payload, 2, 2, signed=True) == -128
    assert standalone._read_be(payload, 0, 2) == 0x0102
    assert standalone._read_le(payload, -1, 2) is None
    assert standalone._read_be(payload, 100, 2) is None
    assert standalone._read_str(payload, 4, 20) == "text"
    timestamp = standalone._safe_timestamp(2026, 8, 5, 22, 30)
    assert standalone._format_dt(timestamp) == "2026-08-05 22:30:00"
    assert standalone._safe_timestamp(2026, 13, 1, 0, 0) is None
    assert standalone._format_dt(None) == "Unknown"


def test_runtime_parser_parses_plausible_packet() -> None:
    payload = bytearray(0x68)
    payload[0:2] = struct.pack("<h", -120)
    payload[2:4] = struct.pack("<h", 340)
    payload[4:8] = bytes((2, 0x0E, 0x1A, 0x19))
    payload[0x0C:0x0E] = struct.pack("<H", 154)
    payload[0x0E:0x12] = struct.pack("<I", 1234)
    payload[0x12:0x16] = struct.pack("<I", 5678)
    payload[0x16:0x1A] = struct.pack("<I", 345)
    payload[0x1A:0x1E] = struct.pack("<I", 678)
    payload[0x29:0x2D] = struct.pack("<I", 5151)
    payload[0x2D:0x31] = struct.pack("<I", 4107)
    payload[0x4A:0x4C] = struct.pack("<H", 800)
    payload[0x4C:0x4E] = bytes((1, 9))
    payload[0x4E:0x50] = b"\x12\x34"
    payload[0x51:0x5D] = b"202608052230"
    payload[0x5E:0x60] = struct.pack("<H", 77)
    payload[0x5F] = 3
    payload[0x60] = 1
    payload[0x62:0x64] = struct.pack("<H", 100)
    payload[0x64:0x66] = struct.pack("<H", 200)
    payload[0x66:0x68] = struct.pack("<H", 8080)
    result = standalone.parse_runtime_info(payload)
    assert result["grid_power_w"] == -120
    assert result["battery_power_w"] == 340
    assert result["work_mode_label"] == "Charging"
    assert result["daily_charge_kwh"] == 12.34
    assert result["power_rating_w"] == 800
    assert result["firmware_version"] == "v1.9"
    assert result["build_code"] == 0x1234
    assert result["firmware_build"] == "2026-08-05 22:30"
    assert result["api_port"] == 8080
    with pytest.raises(ValueError, match="too short"):
        standalone.parse_runtime_info(bytes(0x67))


def test_device_wifi_system_and_config_parsers() -> None:
    assert standalone.parse_device_info(b"type=HMG-50, sn=123, ignored\x00") == {
        "type": "HMG-50",
        "sn": "123",
    }
    assert standalone.parse_wifi_info(b" Home ") == {
        "ssid": "Home",
        "connected": True,
    }
    assert standalone.parse_wifi_info(b"") == {
        "ssid": "Not connected",
        "connected": False,
    }
    system = bytearray(19)
    system[0] = 7
    system[2:18] = struct.pack(
        "<HHHHHHHH", 50, 230, 0, 20, 21, 22, 23, 24
    )
    system[18] = 2
    parsed_system = standalone.parse_system_data(system)
    assert parsed_system["line_frequency_hz"] == 50
    assert parsed_system["ac_voltage_v"] == 230
    assert parsed_system["temperatures_c"] == [20, 21, 22, 23, 24]
    assert parsed_system["work_mode"] == 2
    config = bytearray(17)
    config[0:2] = b"\x02\x03"
    config[4] = 4
    config[5:8] = b"\x05\x06\x07"
    config[8] = 1
    config[12] = 1
    config[16] = 9
    assert standalone.parse_config_data(config) == {
        "mode": 2,
        "flags": 3,
        "config_status": 4,
        "status_bytes": "050607",
        "enable_flag_1": True,
        "enable_flag_2": True,
        "config_value": 9,
    }


def test_bms_parser_parses_cells_and_rejects_short_payload() -> None:
    payload = bytearray(82)
    payload[0:20] = struct.pack(
        "<HHHhHHHHhH",
        215,
        571,
        500,
        900,
        82,
        99,
        5120,
        5037,
        -123,
        24,
    )
    payload[26:28] = struct.pack("<H", 7)
    payload[28:32] = struct.pack("<I", 0x12345678)
    payload[32:36] = struct.pack("<I", 7_200_000)
    payload[38:48] = struct.pack("<HHHHH", 31, 21, 22, 23, 24)
    for index in range(17):
        payload[48 + index * 2 : 50 + index * 2] = struct.pack(
            "<H", 3140 + index
        )
    result = standalone.parse_bms_data(payload)
    assert result["bms_version"] == 215
    assert result["voltage_limit_v"] == 57.1
    assert result["battery_current_a"] == -12.3
    assert result["cell_voltages_v"][0] == "3.140"
    assert len(result["cell_voltages_v"]) == 17
    with pytest.raises(ValueError, match="too short"):
        standalone.parse_bms_data(bytes(79))


def test_log_parsers_skip_zero_records_and_report_latest() -> None:
    error_record = struct.pack(
        "<HBBBBB", 2026, 8, 5, 22, 31, 9
    ) + bytes.fromhex("01020304050607")
    error_payload = bytes(14) + bytes(14) + error_record
    error = standalone.parse_error_log(error_payload)
    assert error["record_count"] == 1
    assert error["latest_error"]["error_code"] == 9
    assert error["latest_error"]["timestamp"] == "2026-08-05 22:31:00"
    event_record = struct.pack("<HBBBBBH", 2026, 8, 5, 22, 32, 3, 0x1234)
    event = standalone.parse_event_log(bytes(14) + event_record)
    assert event["record_count"] == 1
    assert event["latest_event"]["type"] == 3
    assert event["latest_event"]["code"] == 0x1234


def test_meter_and_network_parsers() -> None:
    assert standalone.parse_meter_ip(b"") == {
        "ip_address": "Not configured",
        "configured": False,
    }
    assert standalone.parse_meter_ip(bytes([0xFF]) * 16)["configured"] is False
    assert standalone.parse_meter_ip(b"192.0.2.1\x00padding") == {
        "ip_address": "192.0.2.1",
        "configured": True,
    }
    assert standalone.parse_network_info(
        b"ip:192.0.2.10,gate:192.0.2.1,mask:255.255.255.0,dns:192.0.2.53,x:ignored"
    ) == {
        "raw": "ip:192.0.2.10,gate:192.0.2.1,mask:255.255.255.0,dns:192.0.2.53,x:ignored",
        "ip": "192.0.2.10",
        "gateway": "192.0.2.1",
        "mask": "255.255.255.0",
        "dns": "192.0.2.53",
    }


def test_flatten_metrics_and_summary_table() -> None:
    flattened = standalone.flatten_metrics(
        {
            "battery": {"soc": 80, "cells": [3.1, 3.2]},
            "events": [{"code": 1}],
            "none": None,
        }
    )
    assert flattened == {
        "battery.soc": "80",
        "battery.cells": "3.1, 3.2",
        "events[0].code": "1",
        "none": "",
    }
    table = standalone.render_summary_table(
        ["A", "B"], {"A": {"soc": 80}, "B": {"soc": 70, "power": 10}}
    )
    assert "Metric" in table
    assert "soc" in table
    assert "power" in table
    assert standalone.render_summary_table(["A"], {}) == "No data collected."


class FakeApi:
    def __init__(self) -> None:
        self.write_calls = []
        self.disconnect_calls = []
        self.fail_disconnect = False

    async def bluetooth_gatt_write(
        self, address, handle, frame, response=False
    ):
        self.write_calls.append((address, handle, frame, response))

    async def bluetooth_device_disconnect(self, address):
        self.disconnect_calls.append(address)
        if self.fail_disconnect:
            raise TimeoutAPIError


@pytest.mark.asyncio
async def test_session_notification_resolves_matching_pending_future() -> None:
    api = FakeApi()
    device = standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery")
    session = standalone.BLEDeviceSession(api, device, 1, 1.0, 1.0)
    future = asyncio.get_running_loop().create_future()
    session._pending[0x14].append(future)
    packet = standalone.create_command_frame(0x14, b"reply")
    session._handle_notification(1, bytearray(packet[:3]))
    assert future.done() is False
    session._handle_notification(1, bytearray(packet[3:]))
    assert await future == b"reply"
    assert session._pending[0x14] == deque()


def test_session_notification_discards_malformed_and_unsolicited_frames() -> None:
    async def run() -> None:
        session = standalone.BLEDeviceSession(
            FakeApi(),
            standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery"),
            1,
            1.0,
            1.0,
        )
        malformed = bytearray(standalone.create_command_frame(0x03))
        malformed[-1] ^= 0xFF
        session._handle_notification(1, malformed)
        session._handle_notification(
            1, bytearray(standalone.create_command_frame(0x03))
        )

    asyncio.run(run())


@pytest.mark.asyncio
async def test_session_send_command_writes_frame_and_cleans_queue_on_timeout(
    monkeypatch,
) -> None:
    api = FakeApi()
    device = standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery")
    session = standalone.BLEDeviceSession(api, device, 1, 1.0, 1.0)
    with pytest.raises(RuntimeError, match="TX characteristic"):
        await session.send_command(0x03, "runtime")
    session._tx_handle = 42

    async def immediate_timeout(awaitable, timeout):
        awaitable.cancel()
        raise asyncio.TimeoutError

    monkeypatch.setattr(standalone.asyncio, "wait_for", immediate_timeout)
    with pytest.raises(asyncio.TimeoutError):
        await session.send_command(0x03, "runtime", b"\x01")
    assert api.write_calls == [
        (1, 42, standalone.create_command_frame(0x03, b"\x01"), False)
    ]
    assert session._pending[0x03] == deque()


@pytest.mark.asyncio
async def test_session_close_fails_pending_requests_and_is_idempotent() -> None:
    api = FakeApi()
    api.fail_disconnect = True
    device = standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery")
    session = standalone.BLEDeviceSession(api, device, 1, 1.0, 1.0)
    future = asyncio.get_running_loop().create_future()
    session._pending[0x03].append(future)
    flags = {"notify": 0, "remove": 0, "connection": 0}

    async def stop_notify():
        flags["notify"] += 1
        raise RuntimeError("already stopped")

    session._stop_notify = stop_notify
    session._notify_remove = lambda: flags.__setitem__(
        "remove", flags["remove"] + 1
    )
    session._connection_unsub = lambda: flags.__setitem__(
        "connection", flags["connection"] + 1
    )
    await session.close()
    with pytest.raises(RuntimeError, match="Session closed"):
        await future
    await session.close()
    assert flags == {"notify": 1, "remove": 1, "connection": 1}
    assert api.disconnect_calls == [1]


def test_build_parser_has_isolated_defaults() -> None:
    args = standalone.build_parser().parse_args([])
    assert args.host == standalone.DEFAULT_PROXY_HOST
    assert args.port == standalone.DEFAULT_PROXY_PORT
    assert args.target == []
