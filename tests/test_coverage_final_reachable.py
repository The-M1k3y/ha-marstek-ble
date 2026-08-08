"""Tests for the final reachable branches left by the coverage audit."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from bleak.backends.device import BLEDevice
from homeassistant.core import HomeAssistant

import custom_components.marstek_ble as integration
from custom_components.marstek_ble import coordinator as coordinator_module
from custom_components.marstek_ble.const import DOMAIN, MIN_MEDIUM_POLL_INTERVAL
from custom_components.marstek_ble.coordinator import MarstekDataUpdateCoordinator
from custom_components.marstek_ble.entity import EntityPlan, ProductDeviceSpec, ProductProfile
from custom_components.marstek_ble.marstek_device import (
    MarstekBLEDevice,
    MarstekData,
    MarstekProtocol,
)
from custom_components.marstek_ble.schema import (
    PacketSchema,
    RepeatedSectionSource,
    repeated_section_field,
)
from standalone_test import marstek_basic_info as standalone


def _ble() -> BLEDevice:
    return BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")


def _coordinator() -> tuple[HomeAssistant, BLEDevice, MarstekDataUpdateCoordinator]:
    hass = HomeAssistant()
    ble = _ble()
    hass._ble_devices[ble.address] = ble
    coordinator = MarstekDataUpdateCoordinator(
        hass=hass,
        logger=logging.getLogger("test.final-reachable"),
        address=ble.address,
        device=ble,
        device_name="Battery",
        poll_interval=2,
        medium_poll_interval=60,
    )
    return hass, ble, coordinator


class SetupConfigEntries:
    def __init__(self, entries) -> None:
        self.entries = list(entries)
        self.forwarded = []

    def async_entries(self, domain):
        assert domain == DOMAIN
        return list(self.entries)

    async def async_forward_entry_setups(self, entry, platforms) -> None:
        self.forwarded.append(entry)


class SetupEntry:
    def __init__(self, entry_id: str, address: str, name: str) -> None:
        self.entry_id = entry_id
        self.title = name
        self.data = {
            "address": address,
            "name": name,
            "product_id": "venus",
        }
        self.options = {}
        self.runtime_data = None
        self.unloads = []

    def async_on_unload(self, callback) -> None:
        self.unloads.append(callback)

    def add_update_listener(self, callback):
        return lambda: None


class ReadyCoordinator:
    def __init__(self) -> None:
        self.device = SimpleNamespace(disconnect=self.disconnect)

    def async_start(self):
        return lambda: None

    async def async_wait_ready(self) -> bool:
        return True

    async def disconnect(self) -> None:
        return None


@pytest.mark.asyncio
async def test_setup_duplicate_scan_continues_after_nonduplicate_entry(monkeypatch) -> None:
    hass = HomeAssistant()
    ble = _ble()
    hass._ble_devices[ble.address] = ble
    entry = SetupEntry("entry-1", ble.address, "Battery")
    nonduplicate = SetupEntry("entry-2", "11:22:33:44:55:66", "Other")
    duplicate = SetupEntry("entry-3", "22:33:44:55:66:77", "Battery")
    hass.config_entries = SetupConfigEntries([entry, nonduplicate, duplicate])
    coordinator = ReadyCoordinator()
    monkeypatch.setattr(
        integration,
        "MarstekDataUpdateCoordinator",
        lambda **kwargs: coordinator,
    )

    assert await integration.async_setup_entry(hass, entry) is True
    assert hass.config_entries.forwarded == [entry]


def test_medium_poll_interval_clamps_values_below_minimum() -> None:
    _, _, coordinator = _coordinator()

    assert (
        coordinator._sanitize_medium_poll_interval(
            MIN_MEDIUM_POLL_INTERVAL - 1,
            fast_poll_interval=1,
        )
        == MIN_MEDIUM_POLL_INTERVAL
    )


def test_legacy_runtime_parser_supports_60_to_99_byte_format() -> None:
    payload = bytearray(60)
    payload[15] = 0b11
    payload[16] = 1
    payload[20:22] = (321).to_bytes(2, "little")
    payload[28] = 1
    payload[33:35] = (-25).to_bytes(2, "little", signed=True)
    payload[35:37] = (412).to_bytes(2, "little", signed=True)
    data = MarstekData()

    assert MarstekProtocol._parse_runtime_info(bytes(payload), data, 1.0) is True
    assert data.out1_power == 321.0
    assert data.temp_low == -2.5
    assert data.temp_high == 41.2
    assert data.wifi_connected is True
    assert data.mqtt_connected is True
    assert data.out1_active is True
    assert data.extern1_connected is True
    assert data.grid_power is None
    assert data.product_code is None


def test_reset_disconnect_timer_without_previous_timer(monkeypatch) -> None:
    device = MarstekBLEDevice(_ble(), "Battery")
    scheduled = SimpleNamespace(cancel=lambda: None)
    calls = []

    class Loop:
        def call_later(self, delay, callback):
            calls.append((delay, callback))
            return scheduled

    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.asyncio.get_event_loop",
        lambda: Loop(),
    )

    device._reset_disconnect_timer()

    assert calls[0][0] == 30.0
    assert device._disconnect_timer is scheduled


@pytest.mark.asyncio
async def test_disconnect_connected_client_without_notifications() -> None:
    class Client:
        def __init__(self) -> None:
            self.is_connected = True
            self.disconnect_calls = 0

        async def disconnect(self) -> None:
            self.disconnect_calls += 1
            self.is_connected = False

    device = MarstekBLEDevice(_ble(), "Battery")
    client = Client()
    device._client = client
    device._notifications_started = False

    await device.disconnect()

    assert client.disconnect_calls == 1
    assert device._client is None


def test_nested_repeated_entity_keys_include_parent_repeated_key() -> None:
    packet = PacketSchema("nested", 0x01)

    @dataclass(slots=True)
    class Leaf:
        value: int | None = None

    @dataclass(slots=True)
    class Parent:
        children: list[Leaf] = repeated_section_field(
            Leaf,
            count=1,
            sources={packet: RepeatedSectionSource(0, 1)},
        )

    @dataclass(slots=True)
    class Root:
        parents: list[Parent] = repeated_section_field(
            Parent,
            count=1,
            sources={packet: RepeatedSectionSource(0, 1)},
        )

    profile = ProductProfile(
        product_id="nested-repeated",
        device=ProductDeviceSpec("Marstek", "Test"),
        data_type=Root,
        packets=(packet,),
    )

    plan = profile.build_entity_plan(Root())

    assert plan.repeated_counts == {"parents": 1, "parents.0.children": 1}


def test_expansion_detection_tolerates_non_dataclass_repeated_items() -> None:
    packet = PacketSchema("values", 0x01)

    @dataclass(slots=True)
    class Data:
        values: list[int] = repeated_section_field(
            int,
            count=1,
            sources={packet: RepeatedSectionSource(0, 1)},
        )

    profile = ProductProfile(
        product_id="scalar-repeated",
        device=ProductDeviceSpec("Marstek", "Test"),
        data_type=Data,
        packets=(packet,),
    )
    plan = EntityPlan((), (), {"values": 1})

    assert profile.detect_expansion_increases(Data(), plan) == ()


class AdvertisementClient:
    def __init__(self, advertisements) -> None:
        self.advertisements = list(advertisements)
        self.unsubscribe_calls = 0

    def subscribe_bluetooth_le_advertisements(self, callback):
        for advertisement in self.advertisements:
            callback(advertisement)

        def unsubscribe():
            self.unsubscribe_calls += 1

        return unsubscribe


@pytest.mark.asyncio
async def test_target_discovery_ignores_nonmatching_advertisement_before_match() -> None:
    from aioesphomeapi.model import BluetoothLEAdvertisement

    client = AdvertisementClient(
        [
            BluetoothLEAdvertisement(1, name="Other", rssi=-60, service_uuids=[]),
            BluetoothLEAdvertisement(2, name="Battery", rssi=-50, service_uuids=[]),
        ]
    )

    devices, _ = await standalone.discover_devices(
        client,
        [standalone.TargetSpec.from_string("Battery")],
        scan_timeout=0,
        auto_prefix="MST_",
        auto_limit=1,
        log_adv_limit=0,
        case_sensitive_prefix=False,
        use_raw_ads=False,
        keep_subscription=False,
    )

    assert [device.address for device in devices] == [2]


@pytest.mark.asyncio
async def test_session_close_ignores_already_completed_pending_future() -> None:
    class Api:
        async def bluetooth_device_disconnect(self, address):
            return None

    session = standalone.BLEDeviceSession(
        Api(),
        standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery"),
        1,
        1.0,
        1.0,
    )
    future = asyncio.get_running_loop().create_future()
    future.set_result(b"already done")
    session._pending[0x03].append(future)

    await session.close()

    assert future.result() == b"already done"
    assert session._pending == {}


@pytest.mark.asyncio
async def test_notification_handler_contains_parse_frame_failure(monkeypatch) -> None:
    session = standalone.BLEDeviceSession(
        SimpleNamespace(),
        standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery"),
        1,
        1.0,
        1.0,
    )
    packet = standalone.create_command_frame(0x03)
    monkeypatch.setattr(session._decoder, "feed", lambda data: [packet])
    monkeypatch.setattr(
        standalone,
        "parse_frame",
        lambda frame: (_ for _ in ()).throw(ValueError("forced parser failure")),
    )

    session._handle_notification(1, bytearray(packet))

    assert session._pending == {}


def test_network_parser_ignores_malformed_parts_without_colon() -> None:
    assert standalone.parse_network_info(
        b"malformed,ip:192.0.2.1,also-malformed"
    ) == {
        "raw": "malformed,ip:192.0.2.1,also-malformed",
        "ip": "192.0.2.1",
    }
