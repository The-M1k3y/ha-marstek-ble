"""Unit tests for polling, scheduling and notification coordination."""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from homeassistant.core import HomeAssistant

from custom_components.marstek_ble import coordinator as coordinator_module
from custom_components.marstek_ble.const import (
    CMD_BMS_DATA,
    CMD_CONFIG_DATA,
    CMD_CT_POLLING_RATE,
    CMD_DEVICE_INFO,
    CMD_LOCAL_API_STATUS,
    CMD_LOGS,
    CMD_METER_IP,
    CMD_NETWORK_INFO,
    CMD_RUNTIME_INFO,
    CMD_SYSTEM_DATA,
    CMD_TIMER_INFO,
    CMD_WIFI_SSID,
)
from custom_components.marstek_ble.coordinator import MarstekDataUpdateCoordinator
from custom_components.marstek_ble.marstek_device import MarstekProtocol


@pytest.fixture(autouse=True)
def reset_global_backoff() -> None:
    coordinator_module._GLOBAL_BACKOFF_LEVEL = 0
    coordinator_module._GLOBAL_BACKOFF_UNTIL = None


@pytest.fixture
def hass() -> HomeAssistant:
    return HomeAssistant()


@pytest.fixture
def ble_device() -> BLEDevice:
    return BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")


def make_coordinator(hass, ble_device, *, fast=1, medium=60):
    hass._ble_devices[ble_device.address] = ble_device
    return MarstekDataUpdateCoordinator(
        hass=hass,
        logger=logging.getLogger("test"),
        address=ble_device.address,
        device=ble_device,
        device_name="Battery",
        poll_interval=fast,
        medium_poll_interval=medium,
    )


def test_initialization_clamps_intervals_and_schedules_time_poll(hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device, fast=0, medium=999)
    assert coordinator._poll_interval == 1
    assert coordinator._medium_poll_interval == 300
    assert coordinator.update_interval.total_seconds() == 1
    assert coordinator._medium_poll_cycle == 300
    assert len(hass._tracked_intervals) == 1
    assert hass._tracked_intervals[0]["interval"].total_seconds() == 1


def test_set_poll_intervals_reschedules_and_resets_counters(hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device, fast=2, medium=11)
    old_schedule = hass._tracked_intervals[-1]
    coordinator._fast_poll_count = 9
    coordinator._medium_poll_count = 4
    coordinator.set_poll_intervals(10, 5)
    assert coordinator._poll_interval == 10
    assert coordinator._medium_poll_interval == 10
    assert coordinator._medium_poll_cycle == 1
    assert coordinator._fast_poll_count == 0
    assert coordinator._medium_poll_count == 0
    assert old_schedule["cancelled"] is True
    assert len(hass._tracked_intervals) == 2


def test_set_poll_intervals_is_noop_when_values_are_unchanged(hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device, fast=5, medium=60)
    count = len(hass._tracked_intervals)
    coordinator.set_poll_intervals(5, 60)
    assert len(hass._tracked_intervals) == count


@pytest.mark.asyncio
async def test_send_and_sleep_records_success_and_failure(monkeypatch, hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    outcomes = iter([True, False])

    async def send_command(command, payload=b""):
        return next(outcomes)

    async def no_sleep(delay):
        return None

    coordinator.device.send_command = send_command
    monkeypatch.setattr(coordinator_module.asyncio, "sleep", no_sleep)
    await coordinator._send_and_sleep(0x03, b"\x01", delay=0.1)
    with pytest.raises(BleakError):
        await coordinator._send_and_sleep(0x14, delay=0)
    assert [entry["success"] for entry in coordinator._current_poll_commands] == [True, False]
    assert coordinator._current_poll_commands[0]["payload"] == "01"
    assert "Failed to send command" in coordinator._current_poll_commands[1]["error"]


@pytest.mark.asyncio
async def test_safe_send_suppresses_errors(monkeypatch, hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)

    async def fail(*args, **kwargs):
        raise RuntimeError("broken")

    monkeypatch.setattr(coordinator, "_send_and_sleep", fail)
    assert await coordinator._safe_send_and_sleep(0x03) is False


def test_needs_poll_requires_connectable_device(hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    info = SimpleNamespace(device=ble_device)
    assert coordinator._needs_poll(info, None) is True
    hass._ble_devices.clear()
    assert coordinator._needs_poll(info, 10.0) is False


@pytest.mark.asyncio
async def test_time_poll_skips_without_device_and_uses_last_service_info(monkeypatch, hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    hass._ble_devices.clear()
    calls = []

    async def run_poll(info):
        calls.append(info)
        return coordinator.data

    monkeypatch.setattr(coordinator, "_async_run_poll", run_poll)
    await coordinator._async_time_poll(None)
    assert calls == []
    info = SimpleNamespace(device=ble_device)
    coordinator._last_service_info = info
    await coordinator._async_time_poll(None)
    assert calls == [info]


@pytest.mark.asyncio
async def test_poll_cycle_runs_medium_initially_then_by_cycle(monkeypatch, hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device, fast=10, medium=25)
    info = SimpleNamespace(device=ble_device)
    calls = []

    async def fast():
        calls.append("fast")
        coordinator._current_poll_commands.append(
            {"cmd": CMD_RUNTIME_INFO, "success": True, "duration": 0.0}
        )

    async def medium():
        calls.append("medium")
        coordinator._current_poll_commands.append(
            {"cmd": CMD_SYSTEM_DATA, "success": True, "duration": 0.0}
        )

    monkeypatch.setattr(coordinator, "_poll_fast", fast)
    monkeypatch.setattr(coordinator, "_poll_medium", medium)
    await coordinator._async_run_poll(info)
    await coordinator._async_run_poll(info)
    await coordinator._async_run_poll(info)
    assert calls == ["fast", "medium", "fast", "fast", "medium"]
    assert coordinator._fast_poll_count == 3
    assert coordinator._medium_poll_count == 2
    assert coordinator._initial_poll_done is True


def test_backoff_increments_caps_and_clears(monkeypatch, hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    monkeypatch.setattr(coordinator_module.time, "time", lambda: 100.0)
    for _ in range(10):
        coordinator._handle_backoff(True)
    assert coordinator_module._GLOBAL_BACKOFF_LEVEL == 4
    assert coordinator_module._GLOBAL_BACKOFF_UNTIL == 160.0
    coordinator._handle_backoff(False)
    assert coordinator_module._GLOBAL_BACKOFF_LEVEL == 0
    assert coordinator_module._GLOBAL_BACKOFF_UNTIL is None


@pytest.mark.asyncio
async def test_active_global_backoff_skips_poll(monkeypatch, hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    coordinator_module._GLOBAL_BACKOFF_UNTIL = 200.0
    monkeypatch.setattr(coordinator_module.time, "time", lambda: 100.0)

    async def should_not_run():
        raise AssertionError

    monkeypatch.setattr(coordinator, "_poll_fast", should_not_run)
    assert await coordinator._async_run_poll(SimpleNamespace(device=ble_device)) is coordinator.data


@pytest.mark.asyncio
async def test_fast_and_medium_poll_command_sequences(monkeypatch, hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    calls = []

    async def record(command, payload=b"", delay=0.3):
        calls.append((command, payload, delay))
        return True

    monkeypatch.setattr(coordinator, "_safe_send_and_sleep", record)
    await coordinator._poll_fast()
    await coordinator._poll_medium()
    assert calls[:2] == [(CMD_RUNTIME_INFO, b"", 0.1), (CMD_BMS_DATA, b"", 0.1)]
    assert calls[2:] == [
        (CMD_SYSTEM_DATA, b"", 0.3),
        (CMD_WIFI_SSID, b"", 0.3),
        (CMD_CONFIG_DATA, b"", 0.3),
        (CMD_CT_POLLING_RATE, b"", 0.3),
        (CMD_METER_IP, b"\x0B", 0.3),
        (CMD_NETWORK_INFO, b"", 0.3),
        (CMD_DEVICE_INFO, b"", 0.3),
        (CMD_TIMER_INFO, b"", 0.3),
        (CMD_LOGS, b"", 0.3),
    ]


def test_notification_records_result_and_updates_listeners(hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    packet = MarstekProtocol.build_command(0x22, b"\x05")
    coordinator._handle_notification(7, bytearray(packet))
    assert coordinator.data.ct_polling_rate == 5
    assert coordinator._listener_updates == 1
    assert coordinator.device.get_diagnostics()["recent_notifications"][0]["parsed"] is True
    coordinator._handle_notification(7, bytearray(b"bad"))
    assert coordinator._listener_updates == 1
    assert coordinator.device.get_diagnostics()["recent_notifications"][-1]["parsed"] is False


def test_bluetooth_lifecycle_marks_ready_online_and_unavailable(hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    info = SimpleNamespace(device=ble_device)
    coordinator._async_handle_unavailable(info)
    assert coordinator._was_unavailable is True
    assert coordinator.last_update_success is False
    coordinator._async_handle_bluetooth_event(info, "advertisement")
    assert coordinator._ready_event.is_set() is True
    assert coordinator._was_unavailable is False
    assert coordinator.last_update_success is True


@pytest.mark.asyncio
async def test_wait_ready_returns_immediately_when_event_is_set(hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    coordinator._ready_event.set()
    assert await coordinator.async_wait_ready() is True


@pytest.mark.known_issue
@pytest.mark.asyncio
async def test_medium_poll_includes_local_api_status(monkeypatch, hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)
    calls = []

    async def record(command, payload=b"", delay=0.3):
        calls.append(command)
        return True

    monkeypatch.setattr(coordinator, "_safe_send_and_sleep", record)
    await coordinator._poll_medium()
    assert CMD_LOCAL_API_STATUS in calls


@pytest.mark.known_issue
def test_notification_parser_exception_is_contained(hass, ble_device) -> None:
    coordinator = make_coordinator(hass, ble_device)

    class BrokenProtocol:
        @staticmethod
        def parse_notification(data, target):
            raise RuntimeError("malformed parser state")

    coordinator._protocol = BrokenProtocol
    try:
        coordinator._handle_notification(1, bytearray(b"\x73\x05\x23\x03\x56"))
    except RuntimeError as exc:
        pytest.fail(f"parser exception escaped notification callback: {exc}")
