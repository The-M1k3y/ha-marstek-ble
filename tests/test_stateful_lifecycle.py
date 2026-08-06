"""Stateful concurrency and lifecycle tests for the original BLE implementations."""
from __future__ import annotations

import asyncio

import pytest

from bleak.backends.device import BLEDevice

from custom_components.marstek_ble.marstek_device import (
    CHAR_NOTIFY_UUID,
    MarstekBLEDevice,
    MarstekProtocol,
)
from standalone_test import marstek_basic_info as standalone


class IntegrationClient:
    def __init__(self) -> None:
        self.is_connected = True
        self.start_notify_calls = 0
        self.disconnect_calls = 0
        self.write_calls: list[bytes] = []
        self.write_entered = asyncio.Event()
        self.release_write = asyncio.Event()

    async def start_notify(self, uuid, callback) -> None:
        assert uuid == CHAR_NOTIFY_UUID
        self.start_notify_calls += 1

    async def stop_notify(self, uuid) -> None:
        assert uuid == CHAR_NOTIFY_UUID

    async def write_gatt_char(self, uuid, data) -> None:
        self.write_calls.append(bytes(data))
        self.write_entered.set()
        await self.release_write.wait()

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self.is_connected = False


@pytest.mark.asyncio
async def test_concurrent_connection_requests_share_one_establishment(
    monkeypatch,
) -> None:
    ble_device = BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")
    client = IntegrationClient()
    establishment_started = asyncio.Event()
    allow_establishment = asyncio.Event()
    calls = 0

    async def establish(*args, **kwargs):
        nonlocal calls
        calls += 1
        establishment_started.set()
        await allow_establishment.wait()
        return client

    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.establish_connection",
        establish,
    )
    device = MarstekBLEDevice(
        ble_device,
        "Battery",
        notification_callback=lambda sender, data: None,
    )

    tasks = [asyncio.create_task(device._ensure_connected()) for _ in range(20)]
    await establishment_started.wait()
    assert calls == 1
    allow_establishment.set()
    await asyncio.gather(*tasks)

    assert calls == 1
    assert client.start_notify_calls == 1
    assert device.is_connected is True


@pytest.mark.asyncio
async def test_concurrent_commands_are_serialized_and_keep_response_ownership(
    monkeypatch,
) -> None:
    ble_device = BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")
    client = IntegrationClient()
    device = MarstekBLEDevice(ble_device, "Battery")
    device._client = client
    monkeypatch.setattr(device, "_reset_disconnect_timer", lambda: None)

    first = asyncio.create_task(device.send_command(0x03, retry=1))
    await client.write_entered.wait()
    second = asyncio.create_task(device.send_command(0x14, retry=1))
    await asyncio.sleep(0)

    assert len(client.write_calls) == 1
    client.release_write.set()
    await asyncio.sleep(0)
    device.record_notification(1, MarstekProtocol.build_command(0x03), True)
    assert await first is True

    while len(client.write_calls) < 2:
        await asyncio.sleep(0)
    device.record_notification(1, MarstekProtocol.build_command(0x14), True)
    assert await second is True
    assert [packet[3] for packet in client.write_calls] == [0x03, 0x14]


@pytest.mark.asyncio
async def test_wrong_notification_does_not_complete_pending_command(
    monkeypatch,
) -> None:
    ble_device = BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")
    client = IntegrationClient()
    client.release_write.set()
    device = MarstekBLEDevice(ble_device, "Battery")
    device._client = client
    monkeypatch.setattr(device, "_reset_disconnect_timer", lambda: None)

    task = asyncio.create_task(device.send_command(0x14, retry=1))
    await client.write_entered.wait()
    await asyncio.sleep(0)
    device.record_notification(1, MarstekProtocol.build_command(0x03), True)
    await asyncio.sleep(0)
    assert task.done() is False

    device.record_notification(1, MarstekProtocol.build_command(0x14), True)
    assert await task is True


@pytest.mark.asyncio
async def test_cancelled_command_clears_pending_response_state(monkeypatch) -> None:
    ble_device = BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")
    client = IntegrationClient()
    client.release_write.set()
    device = MarstekBLEDevice(ble_device, "Battery")
    device._client = client
    monkeypatch.setattr(device, "_reset_disconnect_timer", lambda: None)

    task = asyncio.create_task(device.send_command(0x03, retry=1))
    await client.write_entered.wait()
    while device._response_event is None:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert device._pending_command is None
    assert device._response_event is None


class StandaloneApi:
    def __init__(self) -> None:
        self.write_calls: list[bytes] = []
        self.write_event = asyncio.Event()
        self.disconnect_calls = 0

    async def bluetooth_gatt_write(self, address, handle, data, response) -> None:
        assert response is False
        self.write_calls.append(bytes(data))
        self.write_event.set()

    async def bluetooth_device_disconnect(self, address) -> None:
        self.disconnect_calls += 1


async def _wait_for_writes(api: StandaloneApi, count: int) -> None:
    while len(api.write_calls) < count:
        api.write_event.clear()
        await api.write_event.wait()


def _standalone_session(api: StandaloneApi) -> standalone.BLEDeviceSession:
    device = standalone.ResolvedDevice("Battery", 1, 0, -40, "MST_TEST")
    session = standalone.BLEDeviceSession(api, device, 0, 1.0, 1.0)
    session._tx_handle = 11
    return session


@pytest.mark.asyncio
async def test_standalone_same_command_waiters_are_completed_fifo() -> None:
    api = StandaloneApi()
    session = _standalone_session(api)

    first = asyncio.create_task(session.send_command(0x03, "first"))
    second = asyncio.create_task(session.send_command(0x03, "second"))
    await _wait_for_writes(api, 2)

    session._handle_notification(
        12, bytearray(standalone.create_command_frame(0x03, b"one"))
    )
    await asyncio.sleep(0)
    assert first.done() is True
    assert second.done() is False

    session._handle_notification(
        12, bytearray(standalone.create_command_frame(0x03, b"two"))
    )
    assert await first == b"one"
    assert await second == b"two"
    await session.close()


@pytest.mark.asyncio
async def test_standalone_fragmented_and_batched_frames_preserve_command_order() -> None:
    api = StandaloneApi()
    session = _standalone_session(api)

    first = asyncio.create_task(session.send_command(0x03, "runtime"))
    second = asyncio.create_task(session.send_command(0x14, "bms"))
    await _wait_for_writes(api, 2)

    runtime = standalone.create_command_frame(0x03, b"runtime")
    bms = standalone.create_command_frame(0x14, b"bms")
    split = len(runtime) // 2
    session._handle_notification(12, bytearray(runtime[:split]))
    assert first.done() is False
    session._handle_notification(12, bytearray(runtime[split:] + bms))

    assert await first == b"runtime"
    assert await second == b"bms"
    await session.close()


@pytest.mark.asyncio
async def test_standalone_close_fails_and_clears_all_pending_waiters() -> None:
    api = StandaloneApi()
    session = _standalone_session(api)

    first = asyncio.create_task(session.send_command(0x03, "runtime"))
    second = asyncio.create_task(session.send_command(0x14, "bms"))
    await _wait_for_writes(api, 2)
    await session.close()

    with pytest.raises(RuntimeError, match="Session closed"):
        await first
    with pytest.raises(RuntimeError, match="Session closed"):
        await second
    assert session._pending == {}
    assert api.disconnect_calls == 1
