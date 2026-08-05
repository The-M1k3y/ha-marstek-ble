"""Unit tests for standalone discovery, GATT and CLI orchestration."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from standalone_test import marstek_basic_info as standalone


class DiscoveryClient:
    def __init__(self, advertisements=(), raw_messages=()) -> None:
        self.advertisements = list(advertisements)
        self.raw_messages = list(raw_messages)
        self.unsubscribed = 0

    def _unsubscribe(self) -> None:
        self.unsubscribed += 1

    def subscribe_bluetooth_le_advertisements(self, callback):
        for advertisement in self.advertisements:
            callback(advertisement)
        return self._unsubscribe

    def subscribe_bluetooth_le_raw_advertisements(self, callback):
        for message in self.raw_messages:
            callback(message)
        return self._unsubscribe


@pytest.mark.asyncio
async def test_discover_devices_matches_explicit_targets_and_keeps_subscription() -> None:
    advertisements = [
        SimpleNamespace(
            address=0xAABBCCDDEEFF,
            address_type=1,
            rssi=-52,
            name="MST_ACCP_TEST",
            service_uuids=[standalone.SERVICE_UUID],
        )
    ]
    client = DiscoveryClient(advertisements=advertisements)
    targets = [standalone.TargetSpec.from_string("MST_ACCP_TEST")]

    devices, unsubscribe = await standalone.discover_devices(
        client,
        targets=targets,
        scan_timeout=0.01,
        auto_prefix="MST_",
        auto_limit=1,
        log_adv_limit=1,
        case_sensitive_prefix=False,
        use_raw_ads=False,
        keep_subscription=True,
    )

    assert [(device.label, device.address, device.address_type) for device in devices] == [
        ("MST_ACCP_TEST", 0xAABBCCDDEEFF, 1)
    ]
    assert unsubscribe is not None
    assert client.unsubscribed == 0
    unsubscribe()
    assert client.unsubscribed == 1


@pytest.mark.asyncio
async def test_discover_devices_auto_filters_prefix_and_deduplicates() -> None:
    advertisements = [
        SimpleNamespace(
            address=1,
            address_type=0,
            rssi=-40,
            name="OTHER",
            service_uuids=[],
        ),
        SimpleNamespace(
            address=2,
            address_type=0,
            rssi=-50,
            name="mst_one",
            service_uuids=[],
        ),
        SimpleNamespace(
            address=2,
            address_type=0,
            rssi=-51,
            name="MST_ONE",
            service_uuids=[],
        ),
        SimpleNamespace(
            address=3,
            address_type=1,
            rssi=-60,
            name="MST_TWO",
            service_uuids=[],
        ),
    ]
    client = DiscoveryClient(advertisements=advertisements)

    devices, unsubscribe = await standalone.discover_devices(
        client,
        targets=[],
        scan_timeout=0.01,
        auto_prefix="MST_",
        auto_limit=2,
        log_adv_limit=0,
        case_sensitive_prefix=False,
        use_raw_ads=False,
        keep_subscription=False,
    )

    assert [(device.address, device.name) for device in devices] == [
        (2, "mst_one"),
        (3, "MST_TWO"),
    ]
    assert unsubscribe is None
    assert client.unsubscribed == 1


@pytest.mark.asyncio
async def test_discover_devices_decodes_raw_advertisement_name() -> None:
    name = b"MST_RAW"
    raw = bytes((len(name) + 1, 0x09)) + name
    advertisement = SimpleNamespace(
        address=4,
        address_type=1,
        rssi=-70,
        data=raw,
    )
    client = DiscoveryClient(
        raw_messages=[SimpleNamespace(advertisements=[advertisement])]
    )

    devices, _ = await standalone.discover_devices(
        client,
        targets=[],
        scan_timeout=0.01,
        auto_prefix="MST_",
        auto_limit=1,
        log_adv_limit=-1,
        case_sensitive_prefix=True,
        use_raw_ads=True,
        keep_subscription=False,
    )

    assert devices[0].name == "MST_RAW"
    assert devices[0].address == 4


@pytest.mark.asyncio
async def test_discover_devices_reports_missing_targets_and_empty_auto_scan() -> None:
    explicit = DiscoveryClient()
    with pytest.raises(RuntimeError, match="Did not see advertisements"):
        await standalone.discover_devices(
            explicit,
            targets=[standalone.TargetSpec.from_string("MST_MISSING")],
            scan_timeout=0.001,
            auto_prefix="MST_",
            auto_limit=1,
            log_adv_limit=0,
            case_sensitive_prefix=False,
            use_raw_ads=False,
            keep_subscription=False,
        )
    assert explicit.unsubscribed == 1

    automatic = DiscoveryClient()
    with pytest.raises(RuntimeError, match="No BLE devices"):
        await standalone.discover_devices(
            automatic,
            targets=[],
            scan_timeout=0.001,
            auto_prefix="MST_",
            auto_limit=1,
            log_adv_limit=0,
            case_sensitive_prefix=False,
            use_raw_ads=False,
            keep_subscription=False,
        )
    assert automatic.unsubscribed == 1


class SessionApi:
    def __init__(
        self,
        *,
        connected=True,
        include_service=True,
        include_rx=True,
    ) -> None:
        self.connected = connected
        self.include_service = include_service
        self.include_rx = include_rx
        self.disconnect_calls = []
        self.connection_unsubscribed = 0
        self.notify_removed = 0
        self.notify_stopped = 0
        self.notify_callback = None

    async def bluetooth_device_connect(self, **kwargs):
        kwargs["on_bluetooth_connection_state"](
            self.connected,
            247,
            0 if self.connected else 1,
        )

        def unsubscribe():
            self.connection_unsubscribed += 1

        return unsubscribe

    async def bluetooth_gatt_get_services(self, address):
        if not self.include_service:
            return SimpleNamespace(services=[])
        characteristics = [
            SimpleNamespace(uuid=standalone.TX_CHAR_UUID, handle=11),
        ]
        if self.include_rx:
            characteristics.append(
                SimpleNamespace(uuid=standalone.RX_CHAR_UUID, handle=12)
            )
        service = SimpleNamespace(
            uuid=standalone.SERVICE_UUID,
            characteristics=characteristics,
        )
        return SimpleNamespace(services=[service])

    async def bluetooth_gatt_start_notify(self, address, handle, callback):
        self.notify_callback = callback

        async def stop_notify():
            self.notify_stopped += 1

        def remove():
            self.notify_removed += 1

        return stop_notify, remove

    async def bluetooth_device_disconnect(self, address):
        self.disconnect_calls.append(address)


@pytest.mark.asyncio
async def test_session_connect_context_manager_and_close() -> None:
    api = SessionApi()
    device = standalone.ResolvedDevice("Battery", 5, 1, -40, "Battery")
    async with standalone.BLEDeviceSession(
        api,
        device,
        7,
        3.0,
        2.0,
    ) as session:
        assert session._tx_handle == 11
        assert session._rx_handle == 12
        assert api.notify_callback == session._handle_notification
    assert api.notify_stopped == 1
    assert api.notify_removed == 1
    assert api.disconnect_calls == [5]
    assert api.connection_unsubscribed == 1


@pytest.mark.asyncio
async def test_session_connect_rejects_connection_service_and_characteristic_failures() -> None:
    device = standalone.ResolvedDevice("Battery", 5, 0, -40, "Battery")
    with pytest.raises(RuntimeError, match="BLE connection"):
        await standalone.BLEDeviceSession(
            SessionApi(connected=False),
            device,
            1,
            1.0,
            1.0,
        ).connect()
    with pytest.raises(RuntimeError, match="service"):
        await standalone.BLEDeviceSession(
            SessionApi(include_service=False),
            device,
            1,
            1.0,
            1.0,
        ).connect()
    with pytest.raises(RuntimeError, match="characteristics"):
        await standalone.BLEDeviceSession(
            SessionApi(include_rx=False),
            device,
            1,
            1.0,
            1.0,
        ).connect()


@pytest.mark.known_issue
@pytest.mark.asyncio
async def test_session_connect_failure_cleans_partial_connection() -> None:
    api = SessionApi(include_service=False)
    device = standalone.ResolvedDevice("Battery", 5, 0, -40, "Battery")
    session = standalone.BLEDeviceSession(api, device, 1, 1.0, 1.0)
    with pytest.raises(RuntimeError, match="service"):
        await session.connect()
    assert api.disconnect_calls == [5]
    assert api.connection_unsubscribed == 1


class CollectionSession:
    outcomes = []
    instances = []

    def __init__(self, *args, **kwargs) -> None:
        self.connect_calls = 0
        self.close_calls = 0
        self.send_calls = []
        self._outcomes = iter(type(self).outcomes)
        type(self).instances.append(self)

    async def connect(self):
        self.connect_calls += 1

    async def send_command(self, command, name, timeout=None):
        self.send_calls.append((command, name, timeout))
        outcome = next(self._outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def close(self):
        self.close_calls += 1


@pytest.fixture(autouse=True)
def reset_collection_session() -> None:
    CollectionSession.outcomes = []
    CollectionSession.instances.clear()


@pytest.mark.asyncio
async def test_collect_device_data_parses_success_and_records_failures(
    monkeypatch,
) -> None:
    specs = [
        standalone.CommandSpec(
            "ok",
            1,
            "OK",
            lambda payload: {"value": payload.decode()},
        ),
        standalone.CommandSpec("timeout", 2, "Timeout", lambda payload: {}),
        standalone.CommandSpec("error", 3, "Error", lambda payload: {}),
    ]
    CollectionSession.outcomes = [
        b"value",
        asyncio.TimeoutError(),
        RuntimeError("bad"),
    ]

    async def no_sleep(delay):
        return None

    monkeypatch.setattr(standalone, "SAFE_COMMANDS", specs)
    monkeypatch.setattr(standalone, "BLEDeviceSession", CollectionSession)
    monkeypatch.setattr(standalone.asyncio, "sleep", no_sleep)
    device = standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery")

    result = await standalone.collect_device_data(
        object(),
        device,
        1,
        2.0,
        3.0,
    )

    assert result == {
        "ok": {"value": "value"},
        "timeout": {"error": "Timeout waiting for Timeout response"},
        "error": {"error": "bad"},
    }
    session = CollectionSession.instances[0]
    assert session.connect_calls == 1
    assert session.close_calls == 1


@pytest.mark.asyncio
async def test_collect_device_data_aborts_after_three_consecutive_failures(
    monkeypatch,
) -> None:
    specs = [
        standalone.CommandSpec(
            str(index),
            index,
            str(index),
            lambda payload: {},
        )
        for index in range(4)
    ]
    CollectionSession.outcomes = [
        RuntimeError("a"),
        RuntimeError("b"),
        RuntimeError("c"),
        b"unused",
    ]

    async def no_sleep(delay):
        return None

    monkeypatch.setattr(standalone, "SAFE_COMMANDS", specs)
    monkeypatch.setattr(standalone, "BLEDeviceSession", CollectionSession)
    monkeypatch.setattr(standalone.asyncio, "sleep", no_sleep)
    device = standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery")

    result = await standalone.collect_device_data(
        object(),
        device,
        1,
        2.0,
        3.0,
    )

    assert list(result) == ["0", "1", "2"]
    assert len(CollectionSession.instances[0].send_calls) == 3
    assert CollectionSession.instances[0].close_calls == 1


@pytest.mark.known_issue
@pytest.mark.asyncio
async def test_collect_device_data_closes_session_when_connect_fails(
    monkeypatch,
) -> None:
    class FailingSession(CollectionSession):
        async def connect(self):
            self.connect_calls += 1
            raise RuntimeError("connect failed")

    monkeypatch.setattr(standalone, "BLEDeviceSession", FailingSession)
    device = standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery")
    with pytest.raises(RuntimeError, match="connect failed"):
        await standalone.collect_device_data(
            object(),
            device,
            1,
            2.0,
            3.0,
        )
    assert FailingSession.instances[-1].close_calls == 1


def run_args(**overrides):
    values = {
        "host": "proxy.test",
        "port": 6053,
        "noise_psk": "key",
        "log_scanner_state": True,
        "scan_mode": "active",
        "target": [],
        "scan_timeout": 1.0,
        "name_prefix": "MST_",
        "max_devices": 2,
        "log_advertisements": 0,
        "case_sensitive_prefix": False,
        "raw_advertisements": False,
        "connect_timeout": 2.0,
        "command_timeout": 3.0,
        "log_level": "INFO",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class RunClient:
    instances = []
    feature_flags = 7

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.connect_calls = []
        self.disconnect_calls = 0
        self.scanner_modes = []
        self.scanner_unsubscribed = 0
        self.api_version = None
        type(self).instances.append(self)

    async def connect(self, login=True):
        self.connect_calls.append(login)

    async def disconnect(self):
        self.disconnect_calls += 1

    async def device_info(self):
        return SimpleNamespace(
            friendly_name="Proxy",
            name="proxy",
            mac_address="00:11:22:33:44:55",
            esphome_version="test",
            bluetooth_proxy_feature_flags_compat=(
                lambda version: type(self).feature_flags
            ),
        )

    def subscribe_bluetooth_scanner_state(self, callback):
        callback(
            SimpleNamespace(
                state=SimpleNamespace(name="RUNNING"),
                mode=SimpleNamespace(name="ACTIVE"),
            )
        )

        def unsubscribe():
            self.scanner_unsubscribed += 1

        return unsubscribe

    def bluetooth_scanner_set_mode(self, mode):
        self.scanner_modes.append(mode)


@pytest.fixture(autouse=True)
def reset_run_client() -> None:
    RunClient.instances.clear()
    RunClient.feature_flags = 7


@pytest.mark.asyncio
async def test_run_collects_devices_handles_per_device_error_and_cleans_up(
    monkeypatch,
    capsys,
) -> None:
    devices = [
        standalone.ResolvedDevice("A", 1, 0, -40, "A"),
        standalone.ResolvedDevice("B", 2, 1, -50, "B"),
    ]
    advertisement_cleanup = {"calls": 0}

    async def discover(*args, **kwargs):
        return devices, lambda: advertisement_cleanup.__setitem__(
            "calls",
            advertisement_cleanup["calls"] + 1,
        )

    async def collect(
        client,
        device,
        ble_feature_flags,
        connect_timeout,
        command_timeout,
    ):
        if device.label == "B":
            raise RuntimeError("unreachable")
        return {"runtime": {"soc": 80}}

    monkeypatch.setattr(standalone, "APIClient", RunClient)
    monkeypatch.setattr(standalone, "discover_devices", discover)
    monkeypatch.setattr(standalone, "collect_device_data", collect)

    await standalone.run(run_args())

    output = capsys.readouterr().out
    assert "Battery Summary" in output
    assert "runtime.soc" in output
    assert "unreachable" in output
    client = RunClient.instances[0]
    assert client.connect_calls == [True]
    assert client.disconnect_calls == 1
    assert client.scanner_unsubscribed == 1
    assert advertisement_cleanup["calls"] == 1
    assert len(client.scanner_modes) == 1


@pytest.mark.asyncio
async def test_run_rejects_proxy_without_bluetooth_features_and_disconnects(
    monkeypatch,
) -> None:
    RunClient.feature_flags = 0
    monkeypatch.setattr(standalone, "APIClient", RunClient)
    with pytest.raises(RuntimeError, match="does not expose Bluetooth proxy"):
        await standalone.run(run_args(log_scanner_state=False))
    assert RunClient.instances[0].disconnect_calls == 1


def test_main_runs_cli_and_handles_keyboard_interrupt(monkeypatch) -> None:
    args = run_args()
    parser = SimpleNamespace(parse_args=lambda: args)
    monkeypatch.setattr(standalone, "build_parser", lambda: parser)
    calls = []

    def run_coroutine(coroutine):
        calls.append(coroutine)
        coroutine.close()

    monkeypatch.setattr(standalone.asyncio, "run", run_coroutine)
    standalone.main()
    assert len(calls) == 1

    def interrupt(coroutine):
        coroutine.close()
        raise KeyboardInterrupt

    monkeypatch.setattr(standalone.asyncio, "run", interrupt)
    standalone.main()


def test_main_converts_unhandled_error_to_exit_status(monkeypatch) -> None:
    args = run_args()
    monkeypatch.setattr(
        standalone,
        "build_parser",
        lambda: SimpleNamespace(parse_args=lambda: args),
    )

    def fail(coroutine):
        coroutine.close()
        raise RuntimeError("failed")

    monkeypatch.setattr(standalone.asyncio, "run", fail)
    with pytest.raises(SystemExit) as exc_info:
        standalone.main()
    assert exc_info.value.code == 1
