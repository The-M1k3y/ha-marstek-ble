"""Focused coverage tests for remaining runtime and defensive edge paths."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from homeassistant.core import HomeAssistant

from custom_components.marstek_ble.marstek_device import (
    CHAR_NOTIFY_UUID,
    MarstekBLEDevice,
    MarstekData,
    MarstekProtocol,
)
from custom_components.marstek_ble.product_coordinator import (
    ProductDataUpdateCoordinator,
)
from custom_components.marstek_ble.products import VENUS_RUNTIME, VenusData
from custom_components.marstek_ble.sensor import MarstekSensor, MarstekTextSensor


class FakeClient:
    """Minimal BLE client with configurable failure points."""

    def __init__(self) -> None:
        self.is_connected = True
        self.start_notify_calls: list[tuple[str, object]] = []
        self.stop_notify_calls: list[str] = []
        self.disconnect_calls = 0
        self.write_calls = 0
        self.start_notify_error: Exception | None = None
        self.stop_notify_error: Exception | None = None
        self.disconnect_error: Exception | None = None
        self.write_error: Exception | None = None

    async def start_notify(self, uuid, callback) -> None:
        self.start_notify_calls.append((uuid, callback))
        if self.start_notify_error is not None:
            raise self.start_notify_error

    async def stop_notify(self, uuid) -> None:
        self.stop_notify_calls.append(uuid)
        if self.stop_notify_error is not None:
            raise self.stop_notify_error

    async def write_gatt_char(self, uuid, data) -> None:
        self.write_calls += 1
        if self.write_error is not None:
            raise self.write_error

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        if self.disconnect_error is not None:
            raise self.disconnect_error
        self.is_connected = False


def _ble_device() -> BLEDevice:
    return BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")


def _entity_coordinator(data) -> SimpleNamespace:
    ble = _ble_device()
    return SimpleNamespace(
        data=data,
        ble_device=ble,
        device_name="Battery",
        address=ble.address,
        last_update_success=True,
    )


def _entry() -> SimpleNamespace:
    return SimpleNamespace(entry_id="entry-1")


def test_numeric_sensor_update_uses_first_available_metadata_and_writes_state() -> None:
    metadata = {
        "missing": None,
        "unknown_age": {
            "command_hex": "0x14",
            "timestamp": "now",
            "age_seconds": None,
            "payload_hex": "01",
        },
        "fresh": {
            "command_hex": "0x03",
            "timestamp": "now",
            "age_seconds": 12.5,
            "payload_hex": "02",
        },
    }
    data = SimpleNamespace(
        battery_soc=73,
        get_field_metadata=lambda field: metadata[field],
    )
    coordinator = _entity_coordinator(data)
    entity = MarstekSensor(
        coordinator,
        _entry(),
        "battery_soc",
        "Battery SOC",
        lambda value: value.battery_soc,
        "%",
        None,
        None,
        stale_fields=["missing", "unknown_age", "fresh"],
    )

    assert entity.native_value == 73
    assert entity._stale_age_seconds() == 12.5
    assert entity._get_representative_metadata() == metadata["unknown_age"]
    assert entity.available is True

    entity._handle_coordinator_update()
    assert entity._write_count == 1
    assert entity.device_info["connections"] == {
        ("bluetooth", "AA:BB:CC:DD:EE:FF")
    }


def test_text_sensor_update_staleness_missing_data_and_device_info() -> None:
    metadata = {
        "empty": {},
        "old": {
            "command_hex": "0x24",
            "timestamp": "then",
            "age_seconds": 601.0,
            "payload_hex": "aa",
        },
    }
    data = SimpleNamespace(
        mode=2,
        get_field_metadata=lambda field: metadata[field],
    )
    coordinator = _entity_coordinator(data)
    entity = MarstekTextSensor(
        coordinator,
        _entry(),
        "mode",
        "Mode",
        lambda value: value.mode,
        stale_fields=["empty", "old"],
    )

    assert entity.native_value == "2"
    assert entity._stale_age_seconds() == 601.0
    assert entity._get_representative_metadata() == metadata["old"]
    assert entity.available is False
    entity._handle_coordinator_update()
    assert entity._write_count == 1
    assert entity.device_info["identifiers"] == {
        ("marstek_ble", "AA:BB:CC:DD:EE:FF")
    }

    coordinator.data = None
    assert entity.available is False
    assert entity._stale_age_seconds() is None
    assert entity._get_representative_metadata() is None


def test_text_sensor_update_without_metadata_logs_unknown_source() -> None:
    data = SimpleNamespace(
        mode=None,
        get_field_metadata=lambda field: None,
    )
    coordinator = _entity_coordinator(data)
    entity = MarstekTextSensor(
        coordinator,
        _entry(),
        "mode",
        "Mode",
        lambda value: value.mode,
    )

    assert entity.native_value is None
    entity._handle_coordinator_update()
    assert entity._write_count == 1


def test_product_coordinator_initializes_selected_runtime() -> None:
    hass = HomeAssistant()
    ble = _ble_device()
    hass._ble_devices[ble.address] = ble

    coordinator = ProductDataUpdateCoordinator(
        hass=hass,
        logger=logging.getLogger("test.product-coordinator"),
        address=ble.address,
        device=ble,
        device_name="Battery",
        product=VENUS_RUNTIME,
        poll_interval=2,
        medium_poll_interval=15,
    )

    assert coordinator.product is VENUS_RUNTIME
    assert isinstance(coordinator.data, VenusData)
    assert coordinator._protocol.runtime is VENUS_RUNTIME
    assert coordinator.device.name == "Battery"
    assert coordinator._poll_interval == 2
    assert coordinator._medium_poll_interval == 15


def test_product_coordinator_contains_parser_exceptions() -> None:
    coordinator = object.__new__(ProductDataUpdateCoordinator)
    coordinator.product = VENUS_RUNTIME
    coordinator.device_name = "Battery"
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.data = VenusData()

    def explode(raw, data):
        raise RuntimeError("parser exploded")

    coordinator._protocol = SimpleNamespace(parse_notification=explode)
    recorded: list[tuple[int, bytes, bool]] = []
    coordinator.device = SimpleNamespace(
        record_notification=lambda sender, data, result: recorded.append(
            (sender, data, result)
        )
    )
    listener_calls: list[bool] = []
    coordinator.async_update_listeners = lambda: listener_calls.append(True)

    raw = bytearray(MarstekProtocol.build_command(0x03))
    ProductDataUpdateCoordinator._handle_notification(coordinator, 9, raw)

    assert recorded == [(9, bytes(raw), False)]
    assert listener_calls == []


def test_protocol_dispatch_contains_unexpected_parser_exception(monkeypatch) -> None:
    def explode(payload, data, timestamp):
        raise RuntimeError("unexpected parser failure")

    monkeypatch.setattr(MarstekProtocol, "_parse_wifi_ssid", explode)
    assert (
        MarstekProtocol.parse_notification(
            MarstekProtocol.build_command(0x08, b"ssid"), MarstekData()
        )
        is False
    )


def test_short_runtime_parser_contains_unpack_exception(monkeypatch) -> None:
    def explode(*args, **kwargs):
        raise RuntimeError("broken unpack")

    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.struct.unpack",
        explode,
    )
    assert MarstekProtocol._parse_runtime_info(bytes(37), MarstekData(), 0.0) is False


def test_legacy_text_parsers_contain_metadata_tracking_failures(monkeypatch) -> None:
    def explode(*args, **kwargs):
        raise RuntimeError("metadata failure")

    monkeypatch.setattr(MarstekProtocol, "_track_field", explode)

    assert MarstekProtocol._parse_device_info(b"type=test", MarstekData(), 0.0) is False
    assert MarstekProtocol._parse_wifi_ssid(b"wifi", MarstekData(), 0.0) is False
    assert MarstekProtocol._parse_meter_ip(b"192.0.2.1", MarstekData(), 0.0) is False
    assert (
        MarstekProtocol._parse_network_info(b"ip:192.0.2.1", MarstekData(), 0.0)
        is False
    )


def test_legacy_network_meter_and_local_api_alternate_paths() -> None:
    data = MarstekData()

    assert MarstekProtocol._parse_meter_ip(b"\xff\xff", data, 1.0) is True
    assert data.meter_ip == "(not set)"

    assert MarstekProtocol._parse_network_info(b"", data, 2.0) is True
    assert data.network_info == ""

    assert (
        MarstekProtocol._parse_network_info(
            b"ignored, gateway:192.0.2.1,unknown:value", data, 3.0
        )
        is True
    )
    assert data.gateway == "192.0.2.1"

    assert MarstekProtocol._parse_local_api_status(b"\x00\x34\x12", data, 4.0)
    assert data.local_api_status == "disabled/4660"


@pytest.mark.asyncio
async def test_ensure_connected_reuses_last_device_when_refresh_returns_none(
    monkeypatch,
) -> None:
    ble = _ble_device()
    client = FakeClient()
    establish_devices: list[BLEDevice] = []

    async def establish(*args, **kwargs):
        establish_devices.append(args[1])
        return client

    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.establish_connection",
        establish,
    )
    device = MarstekBLEDevice(
        ble,
        "Battery",
        ble_device_callback=lambda: None,
    )

    await device._ensure_connected()

    assert establish_devices == [ble]
    assert device.address == ble.address
    assert client.start_notify_calls == []


@pytest.mark.asyncio
async def test_ensure_connected_rejects_missing_last_and_refreshed_device() -> None:
    device = MarstekBLEDevice(
        _ble_device(),
        "Battery",
        ble_device_callback=lambda: None,
    )
    device._ble_device = None

    with pytest.raises(BleakError, match="No connectable BLE device"):
        await device._ensure_connected()


@pytest.mark.asyncio
async def test_notification_setup_failure_contains_cleanup_failure(monkeypatch) -> None:
    client = FakeClient()
    client.start_notify_error = RuntimeError("notify failed")
    client.disconnect_error = RuntimeError("cleanup failed")

    async def establish(*args, **kwargs):
        return client

    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.establish_connection",
        establish,
    )
    device = MarstekBLEDevice(
        _ble_device(),
        "Battery",
        notification_callback=lambda sender, data: None,
    )

    with pytest.raises(RuntimeError, match="notify failed"):
        await device._ensure_connected()

    assert client.disconnect_calls == 1
    assert device._client is None
    assert device._notifications_started is False
    assert device._expected_disconnect is False


def test_unexpected_disconnect_resets_connection_state() -> None:
    device = MarstekBLEDevice(_ble_device(), "Battery")
    client = FakeClient()
    device._client = client
    device._notifications_started = True
    device._expected_disconnect = False

    device._on_disconnect(client)

    assert device._client is None
    assert device._notifications_started is False
    assert device._expected_disconnect is False


def test_reset_disconnect_timer_cancels_previous_and_schedules_replacement(
    monkeypatch,
) -> None:
    device = MarstekBLEDevice(_ble_device(), "Battery")
    previous = SimpleNamespace(cancelled=False)
    previous.cancel = lambda: setattr(previous, "cancelled", True)
    device._disconnect_timer = previous
    device._last_command_time = 100.0

    scheduled = SimpleNamespace(cancelled=False)
    scheduled.cancel = lambda: setattr(scheduled, "cancelled", True)
    calls: list[tuple[float, object]] = []

    class FakeLoop:
        def call_later(self, delay, callback):
            calls.append((delay, callback))
            return scheduled

    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.asyncio.get_event_loop",
        lambda: FakeLoop(),
    )
    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.time.time",
        lambda: 110.0,
    )

    device._reset_disconnect_timer()

    assert previous.cancelled is True
    assert device._disconnect_timer is scheduled
    assert calls[0][0] == 30.0


@pytest.mark.asyncio
async def test_execute_disconnect_handles_connected_and_idle_device() -> None:
    device = MarstekBLEDevice(_ble_device(), "Battery")
    client = FakeClient()
    device._client = client
    device._last_command_time = None
    device._disconnect_timer = SimpleNamespace()

    await device._execute_disconnect()

    assert client.disconnect_calls == 1
    assert device._expected_disconnect is True
    assert device._disconnect_timer is None

    device._client = None
    device._disconnect_timer = SimpleNamespace()
    await device._execute_disconnect()
    assert device._disconnect_timer is None


@pytest.mark.asyncio
async def test_send_command_contains_write_and_disconnect_failures(monkeypatch) -> None:
    device = MarstekBLEDevice(_ble_device(), "Battery")
    client = FakeClient()
    client.write_error = RuntimeError("write failed")
    client.disconnect_error = RuntimeError("disconnect failed")
    device._client = client
    monkeypatch.setattr(device, "_reset_disconnect_timer", lambda: None)

    assert await device.send_command(0x03, retry=1) is False

    diagnostics = device.get_diagnostics()
    assert client.disconnect_calls == 1
    assert device._client is None
    assert diagnostics["overall"]["failure"] == 1
    assert diagnostics["overall"]["last_error"] == "write failed"
    assert diagnostics["recent_commands"][0]["response"] == "error"


@pytest.mark.asyncio
async def test_disconnect_continues_when_stop_notifications_fails() -> None:
    device = MarstekBLEDevice(_ble_device(), "Battery")
    client = FakeClient()
    client.stop_notify_error = RuntimeError("stop failed")
    device._client = client
    device._notifications_started = True

    await device.disconnect()

    assert client.stop_notify_calls == [CHAR_NOTIFY_UUID]
    assert client.disconnect_calls == 1
    assert device._notifications_started is False
    assert device._client is None


@pytest.mark.asyncio
async def test_disconnect_is_noop_for_disconnected_client() -> None:
    device = MarstekBLEDevice(_ble_device(), "Battery")
    client = FakeClient()
    client.is_connected = False
    device._client = client

    await device.disconnect()

    assert client.stop_notify_calls == []
    assert client.disconnect_calls == 0
    assert device._client is None


def test_unknown_notification_and_zero_sent_command_stats_are_diagnostic_safe() -> None:
    device = MarstekBLEDevice(_ble_device(), "Battery")

    device.record_notification(1, b"\x73\x02", False)
    device.record_notification(2, MarstekProtocol.build_command(0x14), True)

    diagnostics = device.get_diagnostics()
    assert diagnostics["recent_notifications"][0]["command"] is None
    assert diagnostics["recent_notifications"][0]["payload_hex"] == ""
    stats = diagnostics["command_stats"]["0x14"]
    assert stats["sent"] == 0
    assert stats["success_rate"] is None
    assert stats["ratio"] == "0/0"
    assert stats["last_success"] is None
    assert stats["last_failure"] is None
    assert stats["last_notification"] is not None
