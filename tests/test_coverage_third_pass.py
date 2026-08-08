"""Third-pass coverage tests for setup, coordinator, and standalone behavior."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from aioesphomeapi.core import APIConnectionError, BluetoothConnectionDroppedError
from aioesphomeapi.model import BluetoothLEAdvertisement
from bleak.backends.device import BLEDevice
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

import custom_components.marstek_ble as integration
from custom_components.marstek_ble import config_flow, coordinator as coordinator_module
from custom_components.marstek_ble import diagnostics, switch
from custom_components.marstek_ble.const import (
    CONF_MEDIUM_POLL_INTERVAL,
    CONF_POLL_INTERVAL,
    CONF_PRODUCT_ID,
    DOMAIN,
    MAX_MEDIUM_POLL_INTERVAL,
    MAX_POLL_INTERVAL,
)
from custom_components.marstek_ble.coordinator import MarstekDataUpdateCoordinator
from standalone_test import marstek_basic_info as standalone


class FakeConfigEntries:
    """Minimal config-entry manager used by integration lifecycle tests."""

    def __init__(self, entries=(), *, unload_result: bool = True) -> None:
        self._entries = list(entries)
        self.unload_result = unload_result
        self.forwarded = []
        self.unloaded = []

    def async_entries(self, domain):
        assert domain == DOMAIN
        return list(self._entries)

    async def async_forward_entry_setups(self, entry, platforms) -> None:
        self.forwarded.append((entry, tuple(platforms)))

    async def async_unload_platforms(self, entry, platforms) -> bool:
        self.unloaded.append((entry, tuple(platforms)))
        return self.unload_result


class FakeEntry:
    """Small ConfigEntry stand-in with unload/update listener support."""

    def __init__(
        self,
        *,
        entry_id: str = "entry-1",
        address: str = "AA:BB:CC:DD:EE:FF",
        name: str = "Battery",
        product_id: str | None = "venus",
    ) -> None:
        self.entry_id = entry_id
        self.title = name
        self.data = {"address": address, "name": name}
        if product_id is not None:
            self.data[CONF_PRODUCT_ID] = product_id
        self.options = {
            CONF_POLL_INTERVAL: 2,
            CONF_MEDIUM_POLL_INTERVAL: 60,
        }
        self.runtime_data = None
        self.unload_callbacks = []

    def async_on_unload(self, callback) -> None:
        self.unload_callbacks.append(callback)

    def add_update_listener(self, callback):
        return lambda: None


class FakeIntegrationCoordinator:
    """Coordinator stand-in for setup/unload behavior."""

    def __init__(self, *, ready: bool = True, disconnect_error: Exception | None = None):
        self.ready = ready
        self.disconnect_error = disconnect_error
        self.started = False
        self.intervals = []
        self.device = SimpleNamespace(disconnect=self.disconnect)

    def async_start(self):
        self.started = True

        def unsubscribe():
            self.started = False

        return unsubscribe

    async def async_wait_ready(self) -> bool:
        return self.ready

    async def disconnect(self) -> None:
        if self.disconnect_error is not None:
            raise self.disconnect_error

    def set_poll_intervals(self, fast: int, medium: int) -> None:
        self.intervals.append((fast, medium))


def _ble() -> BLEDevice:
    return BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")


def _coordinator(*, fast: int = 2, medium: int = 60):
    hass = HomeAssistant()
    ble = _ble()
    hass._ble_devices[ble.address] = ble
    coordinator = MarstekDataUpdateCoordinator(
        hass=hass,
        logger=logging.getLogger("test.coverage-third-pass"),
        address=ble.address,
        device=ble,
        device_name="Battery",
        poll_interval=fast,
        medium_poll_interval=medium,
    )
    return hass, ble, coordinator


@pytest.mark.asyncio
async def test_setup_executes_duplicate_name_warning_branch(monkeypatch) -> None:
    hass = HomeAssistant()
    ble = _ble()
    hass._ble_devices[ble.address] = ble
    entry = FakeEntry()
    other = SimpleNamespace(
        entry_id="entry-2",
        title="Battery",
        data={"address": "11:22:33:44:55:66", "name": "Battery"},
    )
    hass.config_entries = FakeConfigEntries([entry, other])
    coordinator = FakeIntegrationCoordinator()
    monkeypatch.setattr(
        integration,
        "MarstekDataUpdateCoordinator",
        lambda **kwargs: coordinator,
    )

    assert await integration.async_setup_entry(hass, entry) is True
    assert entry.runtime_data is coordinator
    assert coordinator.started is True
    assert hass.data[DOMAIN][entry.entry_id]["product_id"] == "venus"
    assert hass.config_entries.forwarded[0][0] is entry
    assert hass._device_registry.calls[0]["model"] == "Venus E"


@pytest.mark.asyncio
async def test_setup_rejects_missing_device_unsupported_product_and_not_ready(
    monkeypatch,
) -> None:
    hass = HomeAssistant()
    hass.config_entries = FakeConfigEntries()
    missing = FakeEntry()
    with pytest.raises(ConfigEntryNotReady, match="Could not find"):
        await integration.async_setup_entry(hass, missing)

    ble = _ble()
    hass._ble_devices[ble.address] = ble
    unsupported = FakeEntry(product_id="jupiter")
    with pytest.raises(ConfigEntryNotReady, match="Unsupported Marstek product"):
        await integration.async_setup_entry(hass, unsupported)

    not_ready = FakeIntegrationCoordinator(ready=False)
    monkeypatch.setattr(
        integration,
        "MarstekDataUpdateCoordinator",
        lambda **kwargs: not_ready,
    )
    with pytest.raises(ConfigEntryNotReady, match="not advertising"):
        await integration.async_setup_entry(hass, FakeEntry())


@pytest.mark.asyncio
async def test_setup_legacy_entry_uses_runtime_name_fallback(monkeypatch) -> None:
    hass = HomeAssistant()
    ble = _ble()
    hass._ble_devices[ble.address] = ble
    hass.config_entries = FakeConfigEntries()
    entry = FakeEntry(name="Unrecognized Name", product_id=None)
    coordinator = FakeIntegrationCoordinator()
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return coordinator

    monkeypatch.setattr(integration, "MarstekDataUpdateCoordinator", create)

    assert await integration.async_setup_entry(hass, entry)
    assert captured["product"].product_id == "venus"


@pytest.mark.asyncio
async def test_unload_continues_after_disconnect_error_and_cleans_domain_data() -> None:
    hass = HomeAssistant()
    entry = FakeEntry()
    coordinator = FakeIntegrationCoordinator(
        disconnect_error=RuntimeError("disconnect failed")
    )
    hass.config_entries = FakeConfigEntries(unload_result=True)
    hass.data[DOMAIN] = {entry.entry_id: {"coordinator": coordinator}}

    assert await integration.async_unload_entry(hass, entry) is True
    assert DOMAIN not in hass.data


@pytest.mark.asyncio
async def test_unload_without_coordinator_preserves_data_when_platform_unload_fails() -> None:
    hass = HomeAssistant()
    entry = FakeEntry()
    hass.config_entries = FakeConfigEntries(unload_result=False)
    hass.data[DOMAIN] = {entry.entry_id: {"product_id": "venus"}}

    assert await integration.async_unload_entry(hass, entry) is False
    assert entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_entry_update_handles_missing_and_present_runtime_data() -> None:
    hass = HomeAssistant()
    entry = FakeEntry()
    entry.runtime_data = None
    await integration._async_handle_entry_update(hass, entry)

    coordinator = FakeIntegrationCoordinator()
    entry.runtime_data = coordinator
    entry.options = {
        CONF_POLL_INTERVAL: 7,
        CONF_MEDIUM_POLL_INTERVAL: 45,
    }
    await integration._async_handle_entry_update(hass, entry)
    assert coordinator.intervals == [(7, 45)]


@pytest.mark.asyncio
async def test_config_flow_unknown_manual_selection_without_candidates_aborts() -> None:
    flow = config_flow.MarstekBLEConfigFlow()
    result = await flow.async_step_user({"address": "AA:BB:CC:DD:EE:FF"})
    assert result == {"type": "abort", "reason": "no_devices_found"}


def test_diagnostics_manifest_reader_contains_unexpected_resource_error(monkeypatch) -> None:
    def explode(package):
        raise RuntimeError("resource backend failed")

    monkeypatch.setattr(diagnostics.resources, "files", explode)
    assert diagnostics._load_manifest_version() is None


def test_switch_device_info_exposes_bluetooth_identity() -> None:
    coordinator = SimpleNamespace(
        data=SimpleNamespace(),
        ble_device=_ble(),
        device_name="Battery",
        last_update_success=True,
        device=SimpleNamespace(),
    )
    entity = switch.MarstekSwitch(
        coordinator,
        SimpleNamespace(entry_id="entry-1"),
        "output",
        "Output",
        0x05,
        None,
    )
    assert entity.device_info == {
        "identifiers": {(DOMAIN, "AA:BB:CC:DD:EE:FF")},
        "connections": {("bluetooth", "AA:BB:CC:DD:EE:FF")},
        "name": "Battery",
        "manufacturer": "Marstek",
        "model": "Venus E",
    }


@pytest.mark.asyncio
async def test_coordinator_safe_send_success_and_upper_interval_clamps(monkeypatch) -> None:
    hass, ble, coordinator = _coordinator(fast=2, medium=60)

    async def succeed(*args, **kwargs):
        return None

    monkeypatch.setattr(coordinator, "_send_and_sleep", succeed)
    assert await coordinator._safe_send_and_sleep(0x03) is True

    assert coordinator._sanitize_fast_poll_interval(10_000) == MAX_POLL_INTERVAL
    assert (
        coordinator._sanitize_medium_poll_interval(10_000)
        == MAX_MEDIUM_POLL_INTERVAL
    )
    coordinator.set_poll_interval(3)
    assert coordinator._poll_interval == 3


@pytest.mark.asyncio
async def test_time_poll_builds_service_info_from_current_ble_device(monkeypatch) -> None:
    hass, ble, coordinator = _coordinator()
    coordinator._last_service_info = None
    seen = []

    async def run(info):
        seen.append(info)
        return coordinator.data

    monkeypatch.setattr(coordinator, "_async_run_poll", run)
    await coordinator._async_time_poll(None)

    assert len(seen) == 1
    assert seen[0].device is ble


@pytest.mark.asyncio
async def test_poll_cycle_uses_previous_completion_time_and_failure_backoff(monkeypatch) -> None:
    hass, ble, coordinator = _coordinator()
    coordinator._last_poll_completed_at = 90.0
    times = iter((100.0, 101.0, 102.0))
    monkeypatch.setattr(coordinator_module.time, "time", lambda: next(times))
    monkeypatch.setattr(coordinator_module.time, "monotonic", lambda: 50.0)

    async def fast():
        coordinator._current_poll_commands.append(
            {"cmd": 0x03, "success": False, "duration": 0.0}
        )

    async def medium():
        return None

    monkeypatch.setattr(coordinator, "_poll_fast", fast)
    monkeypatch.setattr(coordinator, "_poll_medium", medium)

    assert await coordinator._async_run_poll(SimpleNamespace(device=ble)) is coordinator.data
    assert coordinator_module._GLOBAL_BACKOFF_UNTIL is not None


@pytest.mark.asyncio
async def test_wait_ready_timeout_and_repeated_bluetooth_event(monkeypatch) -> None:
    hass, ble, coordinator = _coordinator()

    async def timeout_wait():
        raise TimeoutError

    monkeypatch.setattr(coordinator._ready_event, "wait", timeout_wait)
    assert await coordinator.async_wait_ready() is False

    coordinator._ready_event.set()
    coordinator._was_unavailable = False
    coordinator._async_handle_bluetooth_event(
        SimpleNamespace(device=ble), "advertisement"
    )
    assert coordinator._ready_event.is_set() is True
    assert coordinator._was_unavailable is False


def test_frame_buffer_recovers_from_complete_frame_with_wrong_identifier() -> None:
    invalid = bytearray(standalone.create_command_frame(0x03))
    invalid[2] = 0x22
    checksum = 0
    for value in invalid[:-1]:
        checksum ^= value
    invalid[-1] = checksum
    valid = standalone.create_command_frame(0x14, b"ok")

    assert standalone.FrameBuffer().feed(bytes(invalid) + valid) == [valid]


def test_target_invalid_hex_falls_back_to_name_and_public_address_label() -> None:
    target = standalone.TargetSpec.from_string("0xNOTHEX")
    assert target.mac_int is None
    assert target.name_upper == "0XNOTHEX"

    device = standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery")
    assert device.address_type_label == "public"


class AdvertisementClient:
    def __init__(self, advertisements=None, raw_messages=None) -> None:
        self.advertisements = list(advertisements or [])
        self.raw_messages = list(raw_messages or [])
        self.unsubscribe_calls = 0

    def _unsubscribe(self) -> None:
        self.unsubscribe_calls += 1

    def subscribe_bluetooth_le_advertisements(self, callback):
        for advertisement in self.advertisements:
            callback(advertisement)
        return self._unsubscribe

    def subscribe_bluetooth_le_raw_advertisements(self, callback):
        for message in self.raw_messages:
            callback(message)
        return self._unsubscribe


@pytest.mark.asyncio
async def test_discover_devices_matches_target_and_unsubscribes() -> None:
    advertisement = BluetoothLEAdvertisement(
        0xAABBCCDDEEFF,
        name="Battery",
        rssi=-45,
        address_type=1,
        service_uuids=[standalone.SERVICE_UUID],
    )
    client = AdvertisementClient([advertisement])
    targets = [standalone.TargetSpec.from_string("Battery")]

    devices, unsubscribe = await standalone.discover_devices(
        client,
        targets,
        scan_timeout=1.0,
        auto_prefix="MST_",
        auto_limit=1,
        log_adv_limit=1,
        case_sensitive_prefix=False,
        use_raw_ads=False,
        keep_subscription=False,
    )

    assert [device.address for device in devices] == [0xAABBCCDDEEFF]
    assert unsubscribe is None
    assert client.unsubscribe_calls == 1


@pytest.mark.asyncio
async def test_discover_devices_raw_auto_mode_decodes_name_and_keeps_subscription() -> None:
    raw_name = b"MST_AUTO_TEST"
    raw_data = bytes((len(raw_name) + 1, 0x09)) + raw_name
    raw_adv = SimpleNamespace(
        address=0x010203040506,
        address_type=0,
        rssi=-55,
        data=raw_data,
    )
    client = AdvertisementClient(
        raw_messages=[SimpleNamespace(advertisements=[raw_adv])]
    )

    devices, unsubscribe = await standalone.discover_devices(
        client,
        [],
        scan_timeout=1.0,
        auto_prefix="mst_",
        auto_limit=1,
        log_adv_limit=1,
        case_sensitive_prefix=False,
        use_raw_ads=True,
        keep_subscription=True,
    )

    assert devices[0].name == "MST_AUTO_TEST"
    assert unsubscribe is not None
    assert client.unsubscribe_calls == 0
    unsubscribe()
    assert client.unsubscribe_calls == 1


class SessionApi:
    def __init__(
        self,
        *,
        connected: bool = True,
        connection_error: int = 0,
        include_service: bool = True,
        include_tx: bool = True,
        include_rx: bool = True,
        disconnect_error: Exception | None = None,
    ) -> None:
        self.connected = connected
        self.connection_error = connection_error
        self.include_service = include_service
        self.include_tx = include_tx
        self.include_rx = include_rx
        self.disconnect_error = disconnect_error
        self.disconnect_calls = 0
        self.stop_calls = 0
        self.remove_calls = 0
        self.unsubscribe_calls = 0
        self.write_calls = []
        self.notification_callback = None

    async def bluetooth_device_connect(self, *, on_bluetooth_connection_state, **kwargs):
        on_bluetooth_connection_state(self.connected, 247, self.connection_error)

        def unsubscribe():
            self.unsubscribe_calls += 1

        return unsubscribe

    async def bluetooth_gatt_get_services(self, address):
        services = []
        if self.include_service:
            characteristics = []
            if self.include_tx:
                characteristics.append(
                    SimpleNamespace(uuid=standalone.TX_CHAR_UUID, handle=41)
                )
            if self.include_rx:
                characteristics.append(
                    SimpleNamespace(uuid=standalone.RX_CHAR_UUID, handle=42)
                )
            services.append(
                SimpleNamespace(
                    uuid=standalone.SERVICE_UUID,
                    characteristics=characteristics,
                )
            )
        return SimpleNamespace(services=services)

    async def bluetooth_gatt_start_notify(self, address, handle, callback):
        self.notification_callback = callback

        async def stop():
            self.stop_calls += 1

        def remove():
            self.remove_calls += 1

        return stop, remove

    async def bluetooth_gatt_write(self, address, handle, frame, response=False):
        self.write_calls.append((address, handle, frame, response))
        if self.notification_callback is not None:
            self.notification_callback(
                42,
                bytearray(
                    standalone.create_command_frame(frame[3], b"response")
                ),
            )

    async def bluetooth_device_disconnect(self, address):
        self.disconnect_calls += 1
        if self.disconnect_error is not None:
            raise self.disconnect_error


def _session(api: SessionApi) -> standalone.BLEDeviceSession:
    return standalone.BLEDeviceSession(
        api,
        standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery"),
        ble_feature_flags=1,
        connect_timeout=1.0,
        command_timeout=1.0,
    )


@pytest.mark.asyncio
async def test_session_context_connects_sends_response_and_closes() -> None:
    api = SessionApi()
    async with _session(api) as session:
        assert session._tx_handle == 41
        assert session._rx_handle == 42
        assert await session.send_command(0x03, "runtime") == b"response"

    assert api.stop_calls == 1
    assert api.remove_calls == 1
    assert api.disconnect_calls == 1
    assert api.unsubscribe_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("api", "message"),
    [
        (SessionApi(connected=False, connection_error=1), "BLE connection"),
        (SessionApi(include_service=False), "service"),
        (SessionApi(include_tx=False), "characteristics"),
        (SessionApi(include_rx=False), "characteristics"),
    ],
)
async def test_session_connect_failure_paths_close_partial_session(api, message) -> None:
    session = _session(api)
    with pytest.raises(RuntimeError, match=message):
        await session.connect()
    assert api.disconnect_calls == 1
    assert api.unsubscribe_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        BluetoothConnectionDroppedError("dropped"),
        APIConnectionError("api gone"),
    ],
)
async def test_session_close_contains_additional_disconnect_errors(error) -> None:
    api = SessionApi(disconnect_error=error)
    session = _session(api)
    await session.close()
    assert api.disconnect_calls == 1


@pytest.mark.asyncio
async def test_collect_device_data_handles_success_timeout_error_and_failure_limit(
    monkeypatch,
) -> None:
    commands = [
        SimpleNamespace(command_id=1, name="first", key="first", timeout=1.0, parser=lambda payload: {"value": payload.decode()}),
        SimpleNamespace(command_id=2, name="second", key="second", timeout=1.0, parser=lambda payload: {}),
        SimpleNamespace(command_id=3, name="third", key="third", timeout=1.0, parser=lambda payload: {}),
        SimpleNamespace(command_id=4, name="fourth", key="fourth", timeout=1.0, parser=lambda payload: {}),
        SimpleNamespace(command_id=5, name="never", key="never", timeout=1.0, parser=lambda payload: {}),
    ]
    monkeypatch.setattr(standalone, "SAFE_COMMANDS", commands)

    class FakeSession:
        instance = None

        def __init__(self, *args, **kwargs):
            self.calls = []
            self.closed = False
            FakeSession.instance = self

        async def connect(self):
            return None

        async def send_command(self, command, description, timeout=None):
            self.calls.append(command)
            if command == 1:
                return b"ok"
            if command in (2, 4):
                raise TimeoutError
            raise RuntimeError("read failed")

        async def close(self):
            self.closed = True

    async def no_sleep(delay):
        return None

    monkeypatch.setattr(standalone, "BLEDeviceSession", FakeSession)
    monkeypatch.setattr(standalone.asyncio, "sleep", no_sleep)

    results = await standalone.collect_device_data(
        SimpleNamespace(),
        standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery"),
        ble_feature_flags=1,
        connect_timeout=1.0,
        command_timeout=1.0,
    )

    assert results["first"] == {"value": "ok"}
    assert "Timeout waiting" in results["second"]["error"]
    assert results["third"] == {"error": "read failed"}
    assert "Timeout waiting" in results["fourth"]["error"]
    assert "never" not in results
    assert FakeSession.instance.calls == [1, 2, 3, 4]
    assert FakeSession.instance.closed is True
