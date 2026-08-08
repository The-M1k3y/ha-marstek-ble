"""Tests for product-specific runtime parsing and coordinator behavior."""

from __future__ import annotations

import struct
from types import SimpleNamespace

import pytest

from custom_components.marstek_ble.product_coordinator import (
    ProductDataUpdateCoordinator,
)
from custom_components.marstek_ble.product_runtime import (
    PollCommand,
    ProductProtocol,
    ProductRuntime,
)
from custom_components.marstek_ble.products import (
    VENUS_PROFILE,
    VENUS_RUNTIME,
    VenusData,
    runtime_for_id,
    runtime_for_name,
)


def frame(command: int, payload: bytes = b"") -> bytes:
    return ProductProtocol.build_command(command, payload)


def test_poll_command_normalizes_payload_and_validates_boundaries() -> None:
    command = PollCommand(0x03, bytearray((1, 2)), delay=0)
    assert command.payload == b"\x01\x02"
    assert command.delay == 0

    with pytest.raises(ValueError, match="fit in one byte"):
        PollCommand(-1)
    with pytest.raises(ValueError, match="fit in one byte"):
        PollCommand(0x100)
    with pytest.raises(ValueError, match="cannot be negative"):
        PollCommand(0x03, delay=-0.1)


def test_runtime_registry_enables_only_venus_and_matches_discovery_names() -> None:
    assert runtime_for_id("venus") is VENUS_RUNTIME
    assert runtime_for_id("jupiter") is None
    assert runtime_for_name("MST_ACCP_TEST") is VENUS_RUNTIME
    assert runtime_for_name("MST_VNSE3_TEST") is VENUS_RUNTIME
    assert runtime_for_name("MST_JPLS_TEST") is None
    assert runtime_for_name(None) is None
    assert VENUS_RUNTIME.matches_name("") is False


def test_venus_runtime_creates_nested_device_specific_data() -> None:
    data = VENUS_RUNTIME.create_data()
    assert isinstance(data, VenusData)
    assert data.battery.battery_voltage is None
    assert data.runtime.out1_power is None
    assert data.network.wifi_ssid is None

    # Temporary compatibility reads keep the not-yet-migrated entity platforms
    # working without making the flat layout the canonical storage model.
    assert data.battery_voltage is None
    with pytest.raises(AttributeError):
        _ = data.not_a_venus_field


def test_runtime_rejects_wrong_data_type_unknown_commands_and_short_payloads() -> None:
    with pytest.raises(TypeError, match="VenusData"):
        VENUS_RUNTIME.parse_payload(0x03, bytes(37), object())

    data = VenusData()
    assert VENUS_RUNTIME.parse_payload(0x7F, b"", data) is None

    with pytest.raises(ValueError, match="too short"):
        VENUS_RUNTIME.parse_payload(0x14, bytes(79), data)


def test_runtime_declarative_parser_updates_only_matching_nested_fields() -> None:
    data = VenusData()
    data.battery.battery_soc = 55

    payload = bytearray(37)
    payload[15] = 0b11
    payload[16] = 1
    payload[20:22] = struct.pack("<H", 777)
    payload[28] = 1

    paths = VENUS_RUNTIME.parse_payload(0x03, bytes(payload), data)
    assert paths is not None
    assert data.runtime.wifi_connected is True
    assert data.runtime.mqtt_connected is True
    assert data.runtime.out1_active is True
    assert data.runtime.out1_power == 777.0
    assert data.runtime.extern1_connected is True
    assert data.runtime.temp_low is None
    assert data.battery.battery_soc == 55
    assert set(paths) == {
        ("runtime", "wifi_connected"),
        ("runtime", "mqtt_connected"),
        ("runtime", "out1_active"),
        ("runtime", "out1_power"),
        ("runtime", "extern1_connected"),
    }


def test_product_protocol_validates_frame_and_tracks_nested_and_legacy_metadata(
    monkeypatch,
) -> None:
    data = VenusData()
    protocol = ProductProtocol(VENUS_RUNTIME)
    monkeypatch.setattr(
        "custom_components.marstek_ble.product_runtime.time.time",
        lambda: 110.0,
    )

    payload = bytearray(80)
    payload[8:10] = struct.pack("<H", 82)
    payload[14:16] = struct.pack("<H", 5037)
    for index in range(16):
        payload[48 + index * 2 : 50 + index * 2] = struct.pack(
            "<H", 3140 + index
        )

    assert protocol.parse_notification(frame(0x14, payload), data) is True
    assert data.battery.battery_soc == 82.0
    assert data.battery.battery_voltage == 50.37
    assert data.battery.cell_voltages[0] == pytest.approx(3.140)

    canonical = data.get_field_metadata(("battery", "battery_soc"))
    legacy = data.get_field_metadata("battery_soc")
    cell = data.get_field_metadata("cell_16_voltage")
    assert canonical is not None
    assert canonical["command_hex"] == "0x14"
    assert canonical["age_seconds"] == 0.0
    assert legacy == canonical
    assert cell is not None
    assert cell["command_hex"] == "0x14"

    invalid = bytearray(frame(0x14, payload))
    invalid[-1] ^= 0xFF
    assert protocol.parse_notification(bytes(invalid), data) is False
    assert protocol.parse_notification(b"\x73", data) is False
    assert protocol.parse_notification(frame(0x7F), data) is False


def test_tracked_product_data_preserves_timestamp_zero(monkeypatch) -> None:
    data = VenusData()
    monkeypatch.setattr(
        "custom_components.marstek_ble.product_runtime.time.time",
        lambda: 50.0,
    )
    data.mark_field_update(
        ("battery", "battery_soc"),
        0x14,
        timestamp=0.0,
        payload=b"\x01\x02",
    )
    metadata = data.get_field_metadata(("battery", "battery_soc"))
    assert metadata == {
        "command": 0x14,
        "command_hex": "0x14",
        "timestamp": "1970-01-01T00:00:00+00:00",
        "age_seconds": 50.0,
        "payload_hex": "0102",
    }
    assert data.get_field_metadata(("battery", "missing")) is None


def test_venus_custom_text_and_network_parsers_use_nested_sections() -> None:
    data = VenusData()
    protocol = ProductProtocol(VENUS_RUNTIME)

    device_info = (
        b"type=HMG-50,id=device-1,sn=serial-1,mac=00:11:22:33:44:55,"
        b"dev_ver=202409090159,hw=3,other=ignored"
    )
    network = (
        b"ip:192.0.2.10,gate:192.0.2.1,"
        b"mask:255.255.255.0,dns:192.0.2.53"
    )

    assert protocol.parse_notification(frame(0x04, device_info), data)
    assert protocol.parse_notification(frame(0x08, b" Test WiFi "), data)
    assert protocol.parse_notification(frame(0x21, b"192.0.2.20\x00"), data)
    assert protocol.parse_notification(frame(0x24, network), data)
    assert protocol.parse_notification(
        frame(0x28, b"\x01\x90\x1f"), data
    )

    assert data.device.device_type == "HMG-50"
    assert data.device.device_id == "device-1"
    assert data.device.serial_number == "serial-1"
    assert data.device.firmware_version == "202409090159"
    assert data.network.wifi_ssid == "Test WiFi"
    assert data.network.meter_ip == "192.0.2.20"
    assert data.network.ip_address == "192.0.2.10"
    assert data.network.gateway == "192.0.2.1"
    assert data.network.subnet_mask == "255.255.255.0"
    assert data.network.dns_server == "192.0.2.53"
    assert data.network.local_api_status == "enabled/8080"

    assert protocol.parse_notification(frame(0x21, b"\xff\xff"), data)
    assert data.network.meter_ip == "(not set)"


def test_venus_text_parsers_preserve_last_alias_in_payload_order() -> None:
    data = VenusData()
    protocol = ProductProtocol(VENUS_RUNTIME)

    assert protocol.parse_notification(
        frame(0x04, b"fw=first,dev_ver=second,fc_ver=third"), data
    )
    assert data.device.firmware_version == "third"

    assert protocol.parse_notification(
        frame(0x24, b"gateway=192.0.2.1,gate=192.0.2.2"), data
    )
    assert data.network.gateway == "192.0.2.2"

    assert protocol.parse_notification(
        frame(0x24, b"gate=192.0.2.3,gateway=192.0.2.4"), data
    )
    assert data.network.gateway == "192.0.2.4"


def test_custom_parser_packet_minimum_lengths_are_enforced() -> None:
    protocol = ProductProtocol(VENUS_RUNTIME)
    data = VenusData()

    assert protocol.parse_notification(frame(0x04, b""), data) is False
    assert protocol.parse_notification(frame(0x21, b""), data) is False
    assert protocol.parse_notification(frame(0x28, b"\x01\x02"), data) is False


def test_runtime_rejects_duplicate_packet_commands() -> None:
    duplicate_profile = type(VENUS_PROFILE)(
        product_id="duplicate",
        device=VENUS_PROFILE.device,
        data_type=VENUS_PROFILE.data_type,
        packets=(
            VENUS_PROFILE.packets[0],
            VENUS_PROFILE.packets[0],
        ),
    )
    with pytest.raises(ValueError, match="more than once"):
        ProductRuntime(
            profile=duplicate_profile,
            fast_poll=(PollCommand(0x03),),
        )


@pytest.mark.asyncio
async def test_product_coordinator_sends_product_poll_schedule_in_order() -> None:
    coordinator = object.__new__(ProductDataUpdateCoordinator)
    calls: list[tuple[int, bytes, float]] = []

    async def send(command: int, payload: bytes = b"", delay: float = 0.3):
        calls.append((command, payload, delay))

    coordinator._safe_send_and_sleep = send
    commands = (
        PollCommand(0x03, b"\x01", 0.1),
        PollCommand(0x14, delay=0.2),
    )

    await ProductDataUpdateCoordinator._poll_commands(coordinator, commands)
    assert calls == [
        (0x03, b"\x01", 0.1),
        (0x14, b"", 0.2),
    ]


@pytest.mark.asyncio
async def test_product_coordinator_uses_runtime_fast_and_medium_schedules() -> None:
    coordinator = object.__new__(ProductDataUpdateCoordinator)
    coordinator.product = VENUS_RUNTIME
    coordinator.device_name = "Battery"
    coordinator.address = "00:11:22:33:44:55"
    seen: list[tuple[PollCommand, ...]] = []

    async def poll(commands: tuple[PollCommand, ...]) -> None:
        seen.append(commands)

    coordinator._poll_commands = poll

    await ProductDataUpdateCoordinator._poll_fast(coordinator)
    await ProductDataUpdateCoordinator._poll_medium(coordinator)
    assert seen == [VENUS_RUNTIME.fast_poll, VENUS_RUNTIME.medium_poll]


def test_product_coordinator_notification_dispatches_selected_protocol() -> None:
    coordinator = object.__new__(ProductDataUpdateCoordinator)
    coordinator.product = VENUS_RUNTIME
    coordinator.device_name = "Battery"
    coordinator.address = "00:11:22:33:44:55"
    coordinator.data = VenusData()

    payload = bytearray(37)
    payload[20:22] = struct.pack("<H", 321)
    raw = frame(0x03, payload)

    recorded = []
    coordinator.device = SimpleNamespace(
        record_notification=lambda sender, data, result: recorded.append(
            (sender, data, result)
        )
    )
    listener_calls = []
    coordinator.async_update_listeners = lambda: listener_calls.append(True)
    coordinator._protocol = ProductProtocol(VENUS_RUNTIME)

    ProductDataUpdateCoordinator._handle_notification(
        coordinator, 7, bytearray(raw)
    )
    assert coordinator.data.runtime.out1_power == 321.0
    assert recorded == [(7, raw, True)]
    assert listener_calls == [True]


def test_product_coordinator_notification_failure_does_not_notify_listeners() -> None:
    coordinator = object.__new__(ProductDataUpdateCoordinator)
    coordinator.product = VENUS_RUNTIME
    coordinator.device_name = "Battery"
    coordinator.address = "00:11:22:33:44:55"
    coordinator.data = VenusData()
    coordinator.device = SimpleNamespace(
        record_notification=lambda sender, data, result: setattr(
            coordinator, "recorded_result", result
        )
    )
    coordinator.async_update_listeners = lambda: setattr(
        coordinator, "listener_called", True
    )
    coordinator.listener_called = False
    coordinator._protocol = SimpleNamespace(
        parse_notification=lambda raw, data: False
    )

    ProductDataUpdateCoordinator._handle_notification(
        coordinator, 7, bytearray(b"\x73")
    )
    assert coordinator.recorded_result is False
    assert coordinator.listener_called is False
