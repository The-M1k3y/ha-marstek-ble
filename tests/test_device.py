"""Unit tests for the original BLE device connection and command layer."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from custom_components.marstek_ble.marstek_device import (
    CHAR_NOTIFY_UUID,
    CHAR_WRITE_UUID,
    MarstekBLEDevice,
    MarstekProtocol,
)


class FakeClient:
    def __init__(self) -> None:
        self.is_connected = True
        self.start_notify_calls = []
        self.stop_notify_calls = []
        self.write_calls = []
        self.disconnect_calls = 0
        self.on_write = None

    async def start_notify(self, uuid, callback) -> None:
        self.start_notify_calls.append((uuid, callback))

    async def stop_notify(self, uuid) -> None:
        self.stop_notify_calls.append(uuid)

    async def write_gatt_char(self, uuid, data) -> None:
        self.write_calls.append((uuid, bytes(data)))
        if self.on_write:
            await self.on_write(bytes(data))

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self.is_connected = False


@pytest.fixture
def ble_device() -> BLEDevice:
    return BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")


def test_initial_state_and_properties(ble_device) -> None:
    device = MarstekBLEDevice(ble_device, "Battery")
    assert device.name == "Battery"
    assert device.address == "AA:BB:CC:DD:EE:FF"
    assert device.is_connected is False
    assert device.get_diagnostics() == {
        "device_name": "Battery",
        "address": "AA:BB:CC:DD:EE:FF",
        "connected": False,
        "overall": {
            "total_sent": 0,
            "success": 0,
            "failure": 0,
            "success_rate": None,
            "ratio": "0/0",
            "last_error": None,
        },
        "recent_commands": [],
        "recent_notifications": [],
        "command_stats": {},
    }


@pytest.mark.asyncio
async def test_ensure_connected_refreshes_device_and_starts_notifications(
    monkeypatch, ble_device
) -> None:
    refreshed = BLEDevice("11:22:33:44:55:66", "refreshed")
    client = FakeClient()
    establish_calls = []

    async def fake_establish(*args, **kwargs):
        establish_calls.append((args, kwargs))
        return client

    callback = lambda sender, data: None
    device = MarstekBLEDevice(
        ble_device,
        "Battery",
        ble_device_callback=lambda: refreshed,
        notification_callback=callback,
    )
    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.establish_connection",
        fake_establish,
    )

    await device._ensure_connected()
    await device._ensure_connected()

    assert device.address == refreshed.address
    assert len(establish_calls) == 1
    assert client.start_notify_calls == [(CHAR_NOTIFY_UUID, callback)]
    assert device.is_connected is True


@pytest.mark.asyncio
async def test_ensure_connected_propagates_ble_errors(monkeypatch, ble_device) -> None:
    async def fail(*args, **kwargs):
        raise BleakError("unreachable")

    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.establish_connection", fail
    )
    device = MarstekBLEDevice(ble_device, "Battery")

    with pytest.raises(BleakError, match="unreachable"):
        await device._ensure_connected()


@pytest.mark.asyncio
async def test_send_command_records_success_after_matching_notification(
    monkeypatch, ble_device
) -> None:
    device = MarstekBLEDevice(ble_device, "Battery")
    client = FakeClient()
    device._client = client

    async def respond(frame: bytes) -> None:
        command = frame[3]
        device.record_notification(
            1, MarstekProtocol.build_command(command, b"\x42"), True
        )

    client.on_write = respond
    monkeypatch.setattr(device, "_reset_disconnect_timer", lambda: None)

    assert await device.send_command(0x22, b"\x01") is True
    assert client.write_calls == [
        (CHAR_WRITE_UUID, MarstekProtocol.build_command(0x22, b"\x01"))
    ]
    diagnostics = device.get_diagnostics()
    assert diagnostics["overall"]["ratio"] == "1/1"
    assert diagnostics["command_stats"]["0x22"]["success"] == 1
    assert diagnostics["recent_commands"][0]["response"] == "received"
    assert diagnostics["recent_notifications"][0]["parsed"] is True


@pytest.mark.asyncio
async def test_send_command_retries_ble_failures(monkeypatch, ble_device) -> None:
    device = MarstekBLEDevice(ble_device, "Battery")
    attempts = 0
    client = FakeClient()

    async def ensure_connected() -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise BleakError(f"failure-{attempts}")
        device._client = client

    async def respond(frame: bytes) -> None:
        device.record_notification(
            1, MarstekProtocol.build_command(frame[3]), True
        )

    async def no_sleep(delay):
        return None

    client.on_write = respond
    monkeypatch.setattr(device, "_ensure_connected", ensure_connected)
    monkeypatch.setattr(device, "_reset_disconnect_timer", lambda: None)
    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.asyncio.sleep",
        no_sleep,
    )

    assert await device.send_command(0x03, retry=3) is True
    assert attempts == 3
    assert device.get_diagnostics()["overall"]["ratio"] == "1/1"


@pytest.mark.asyncio
async def test_disconnect_cancels_timer_stops_notifications_and_disconnects(
    ble_device,
) -> None:
    device = MarstekBLEDevice(ble_device, "Battery")
    client = FakeClient()
    device._client = client
    device._notifications_started = True
    timer = SimpleNamespace(cancelled=False)
    timer.cancel = lambda: setattr(timer, "cancelled", True)
    device._disconnect_timer = timer

    await device.disconnect()

    assert timer.cancelled is True
    assert client.stop_notify_calls == [CHAR_NOTIFY_UUID]
    assert client.disconnect_calls == 1
    assert device.is_connected is False


def test_disconnect_callback_resets_connection_state(ble_device) -> None:
    device = MarstekBLEDevice(ble_device, "Battery")
    device._client = FakeClient()
    device._notifications_started = True
    device._expected_disconnect = True

    device._on_disconnect(device._client)

    assert device._client is None
    assert device._notifications_started is False
    assert device._expected_disconnect is False


def test_record_notification_only_wakes_matching_pending_command(ble_device) -> None:
    device = MarstekBLEDevice(ble_device, "Battery")
    event = asyncio.Event()
    device._pending_command = 0x14
    device._response_event = event

    device.record_notification(1, MarstekProtocol.build_command(0x03), True)
    assert event.is_set() is False
    device.record_notification(
        1, MarstekProtocol.build_command(0x14, b"\x01"), True
    )
    assert event.is_set() is True
    assert device._response_data == MarstekProtocol.build_command(0x14, b"\x01")


def test_command_and_notification_history_is_bounded(ble_device) -> None:
    device = MarstekBLEDevice(ble_device, "Battery")
    for index in range(30):
        command = index % 256
        packet = MarstekProtocol.build_command(command)
        device._record_command_result(
            cmd=command, frame=packet, attempts=1, success=True, error=None
        )
        device.record_notification(index, packet, True)

    diagnostics = device.get_diagnostics()
    assert len(diagnostics["recent_commands"]) == 25
    assert len(diagnostics["recent_notifications"]) == 25
    assert diagnostics["overall"]["total_sent"] == 30


@pytest.mark.known_issue
@pytest.mark.asyncio
async def test_send_command_handles_unexpected_transport_exception(
    monkeypatch, ble_device
) -> None:
    device = MarstekBLEDevice(ble_device, "Battery")

    async def fail() -> None:
        raise RuntimeError("backend invariant failed")

    monkeypatch.setattr(device, "_ensure_connected", fail)
    try:
        result = await device.send_command(0x03, retry=1)
    except RuntimeError as exc:
        pytest.fail(f"unexpected transport exception escaped send_command: {exc}")
    assert result is False
    assert device.get_diagnostics()["overall"]["failure"] == 1


@pytest.mark.known_issue
@pytest.mark.asyncio
async def test_no_response_consumes_configured_retry_budget(
    monkeypatch, ble_device
) -> None:
    device = MarstekBLEDevice(ble_device, "Battery")
    client = FakeClient()
    device._client = client
    monkeypatch.setattr(device, "_reset_disconnect_timer", lambda: None)

    async def immediate_timeout(awaitable, timeout):
        awaitable.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.asyncio.wait_for",
        immediate_timeout,
    )

    assert await device.send_command(0x03, retry=3) is False
    assert len(client.write_calls) == 3
    assert device.get_diagnostics()["recent_commands"][0]["attempts"] == 3


@pytest.mark.known_issue
@pytest.mark.asyncio
async def test_notification_setup_failure_does_not_leave_half_connected_client(
    monkeypatch, ble_device
) -> None:
    client = FakeClient()

    async def fail_start_notify(uuid, callback):
        raise RuntimeError("notify setup failed")

    client.start_notify = fail_start_notify

    async def fake_establish(*args, **kwargs):
        return client

    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.establish_connection",
        fake_establish,
    )
    device = MarstekBLEDevice(
        ble_device, "Battery", notification_callback=lambda sender, data: None
    )

    with pytest.raises(RuntimeError, match="notify setup failed"):
        await device._ensure_connected()
    assert device._client is None
    assert client.disconnect_calls == 1
