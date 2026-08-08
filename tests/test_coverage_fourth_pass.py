"""Fourth-pass tests for remaining reachable coverage branches."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from aioesphomeapi.model import BluetoothLEAdvertisement
from bleak.backends.device import BLEDevice
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant

import custom_components.marstek_ble as integration
from custom_components.marstek_ble import config_flow, coordinator as coordinator_module, switch
from custom_components.marstek_ble.const import DOMAIN, MAX_MEDIUM_POLL_INTERVAL
from custom_components.marstek_ble.coordinator import MarstekDataUpdateCoordinator
from custom_components.marstek_ble.entity import ProductDeviceSpec, ProductProfile
from custom_components.marstek_ble.schema import (
    FieldSource,
    PacketSchema,
    RepeatedSectionSource,
    SectionSource,
    iter_parsed_fields,
    repeated_section_field,
    section_field,
    source_field,
)
from standalone_test import marstek_basic_info as standalone


def _ble(address: str = "AA:BB:CC:DD:EE:FF", name: str = "MST_ACCP_TEST") -> BLEDevice:
    return BLEDevice(address, name)


class FakeConfigEntries:
    def __init__(self, entries=(), *, unload_result: bool = True) -> None:
        self.entries = list(entries)
        self.unload_result = unload_result

    def async_entries(self, domain):
        return list(self.entries)

    async def async_unload_platforms(self, entry, platforms) -> bool:
        return self.unload_result


class FakeEntry:
    def __init__(self, entry_id: str = "entry-1") -> None:
        self.entry_id = entry_id
        self.title = "Battery"
        self.data = {"address": "AA:BB:CC:DD:EE:FF", "name": "Battery"}
        self.options = {}
        self.runtime_data = None


@pytest.mark.asyncio
async def test_unload_success_handles_absent_and_nonempty_domain_data() -> None:
    entry = FakeEntry()

    hass = HomeAssistant()
    hass.config_entries = FakeConfigEntries(unload_result=True)
    assert await integration.async_unload_entry(hass, entry) is True
    assert DOMAIN not in hass.data

    hass = HomeAssistant()
    hass.config_entries = FakeConfigEntries(unload_result=True)
    hass.data[DOMAIN] = {
        entry.entry_id: {"product_id": "venus"},
        "other-entry": {"product_id": "venus"},
    }
    assert await integration.async_unload_entry(hass, entry) is True
    assert hass.data[DOMAIN] == {"other-entry": {"product_id": "venus"}}


@pytest.mark.asyncio
async def test_config_flow_discovery_checks_nonmatching_existing_entry() -> None:
    flow = config_flow.MarstekBLEConfigFlow()
    flow.context = {}
    flow._current_entries = [
        SimpleNamespace(
            data={"name": "Other Battery", "address": "11:22:33:44:55:66"}
        )
    ]
    info = BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="MST_ACCP_TEST",
        device=_ble(),
    )

    result = await flow.async_step_bluetooth(info)

    assert result["type"] == "form"
    assert result["step_id"] == "bluetooth_confirm"


def _coordinator() -> tuple[HomeAssistant, BLEDevice, MarstekDataUpdateCoordinator]:
    hass = HomeAssistant()
    ble = _ble()
    hass._ble_devices[ble.address] = ble
    coordinator = MarstekDataUpdateCoordinator(
        hass=hass,
        logger=logging.getLogger("test.coverage-fourth-pass"),
        address=ble.address,
        device=ble,
        device_name="Battery",
        poll_interval=2,
        medium_poll_interval=60,
    )
    return hass, ble, coordinator


@pytest.mark.asyncio
async def test_send_and_sleep_success_without_delay_and_async_update(monkeypatch) -> None:
    hass, ble, coordinator = _coordinator()

    async def send(command, payload=b""):
        return True

    coordinator.device.send_command = send
    await coordinator._send_and_sleep(0x03, delay=0)
    assert coordinator._current_poll_commands[-1]["success"] is True

    info = SimpleNamespace(device=ble)
    calls = []

    async def run_poll(service_info):
        calls.append(service_info)
        return coordinator.data

    monkeypatch.setattr(coordinator, "_async_run_poll", run_poll)
    assert await coordinator._async_update(info) is coordinator.data
    assert calls == [info]


def test_medium_interval_explicitly_hits_upper_clamp() -> None:
    hass, ble, coordinator = _coordinator()
    assert (
        coordinator._sanitize_medium_poll_interval(
            MAX_MEDIUM_POLL_INTERVAL + 1,
            fast_poll_interval=1,
        )
        == MAX_MEDIUM_POLL_INTERVAL
    )


def test_switch_successful_turn_off_updates_assumed_state() -> None:
    class Device:
        async def send_command(self, command, payload=b""):
            return True

    coordinator = SimpleNamespace(
        data=SimpleNamespace(),
        ble_device=_ble(),
        device_name="Battery",
        last_update_success=True,
        device=Device(),
    )
    entity = switch.MarstekSwitch(
        coordinator,
        SimpleNamespace(entry_id="entry-1"),
        "output",
        "Output",
        0x05,
        None,
    )

    async def run() -> None:
        await entity.async_turn_off()

    import asyncio

    asyncio.run(run())
    assert entity.is_on is False
    assert entity._write_count == 1


def test_schema_skips_nested_section_without_source_for_selected_packet() -> None:
    selected = PacketSchema("selected", 0x01, 1, 1)
    other = PacketSchema("other", 0x02, 1, 1)

    @dataclass(slots=True)
    class Child:
        value: int | None = source_field(
            sources={selected: FieldSource(0, "<B")}
        )

    @dataclass(slots=True)
    class Root:
        child: Child = section_field(
            Child,
            sources={other: SectionSource(0)},
        )

    data = Root()
    assert tuple(iter_parsed_fields(b"\x42", selected, data)) == ()
    assert data.child.value is None


def test_entity_plan_repeated_section_without_item_name_factory() -> None:
    packet = PacketSchema("items", 0x01, 1, 1)

    @dataclass(slots=True)
    class Item:
        value: int | None = source_field(
            sources={packet: FieldSource(0, "<B")}
        )

    @dataclass(slots=True)
    class Data:
        items: list[Item] = repeated_section_field(
            Item,
            count=1,
            sources={packet: RepeatedSectionSource(0, 1)},
        )

    profile = ProductProfile(
        product_id="plain-repeated",
        device=ProductDeviceSpec("Marstek", "Test"),
        data_type=Data,
        packets=(packet,),
    )
    plan = profile.build_entity_plan(Data())
    assert plan.repeated_counts == {"items": 1}


def test_frame_buffer_direct_validation_rejects_non_start_byte() -> None:
    buffer = standalone.FrameBuffer()
    buffer._buffer.extend(b"xxxxx")
    assert buffer._is_complete_valid_frame(0) is False


class AdvertisementClient:
    def __init__(self, advertisements=(), raw_messages=()) -> None:
        self.advertisements = list(advertisements)
        self.raw_messages = list(raw_messages)
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
async def test_target_discovery_handles_duplicate_advertisement_and_log_limit() -> None:
    advertisement = BluetoothLEAdvertisement(
        0xAABBCCDDEEFF,
        name="Battery",
        rssi=-45,
        address_type=1,
        service_uuids=[],
    )
    client = AdvertisementClient([advertisement, advertisement])

    devices, _ = await standalone.discover_devices(
        client,
        [standalone.TargetSpec.from_string("Battery")],
        scan_timeout=0,
        auto_prefix="MST_",
        auto_limit=1,
        log_adv_limit=1,
        case_sensitive_prefix=False,
        use_raw_ads=False,
        keep_subscription=False,
    )

    assert len(devices) == 1
    assert client.unsubscribe_calls == 1


@pytest.mark.asyncio
async def test_auto_discovery_filters_prefix_duplicate_and_returns_partial_result() -> None:
    advertisements = [
        BluetoothLEAdvertisement(1, name="OTHER", rssi=-60, service_uuids=[]),
        BluetoothLEAdvertisement(2, name="MST_ONE", rssi=-50, service_uuids=[]),
        BluetoothLEAdvertisement(2, name="MST_ONE", rssi=-49, service_uuids=[]),
    ]
    client = AdvertisementClient(advertisements)

    devices, _ = await standalone.discover_devices(
        client,
        [],
        scan_timeout=0,
        auto_prefix="MST_",
        auto_limit=2,
        log_adv_limit=1,
        case_sensitive_prefix=True,
        use_raw_ads=False,
        keep_subscription=False,
    )

    assert [device.name for device in devices] == ["MST_ONE"]


@pytest.mark.asyncio
async def test_raw_discovery_name_decoder_boundary_and_non_name_fields() -> None:
    raw_advertisements = [
        SimpleNamespace(address=1, address_type=0, rssi=-60, data=b"\x00"),
        SimpleNamespace(address=2, address_type=0, rssi=-61, data=b"\x05\x09A"),
        SimpleNamespace(address=3, address_type=0, rssi=-62, data=b"\x02\x01X"),
    ]
    client = AdvertisementClient(
        raw_messages=[SimpleNamespace(advertisements=raw_advertisements)]
    )

    devices, _ = await standalone.discover_devices(
        client,
        [],
        scan_timeout=0,
        auto_prefix="",
        auto_limit=3,
        log_adv_limit=0,
        case_sensitive_prefix=False,
        use_raw_ads=True,
        keep_subscription=False,
    )

    assert len(devices) == 3
    assert all(device.name for device in devices)


@pytest.mark.asyncio
async def test_session_connection_callback_ignores_second_state_update() -> None:
    class Api:
        async def bluetooth_device_connect(
            self, *, on_bluetooth_connection_state, **kwargs
        ):
            on_bluetooth_connection_state(True, 247, 0)
            on_bluetooth_connection_state(False, 247, 1)
            return lambda: None

        async def bluetooth_gatt_get_services(self, address):
            return SimpleNamespace(
                services=[
                    SimpleNamespace(
                        uuid=standalone.SERVICE_UUID,
                        characteristics=[
                            SimpleNamespace(uuid=standalone.TX_CHAR_UUID, handle=41),
                            SimpleNamespace(uuid=standalone.RX_CHAR_UUID, handle=42),
                        ],
                    )
                ]
            )

        async def bluetooth_gatt_start_notify(self, address, handle, callback):
            async def stop():
                return None

            return stop, lambda: None

        async def bluetooth_device_disconnect(self, address):
            return None

    session = standalone.BLEDeviceSession(
        Api(),
        standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery"),
        1,
        1.0,
        1.0,
    )
    await session.connect()
    assert session._tx_handle == 41
    await session.close()


@pytest.mark.asyncio
async def test_notification_does_not_complete_already_done_pending_future() -> None:
    session = standalone.BLEDeviceSession(
        SimpleNamespace(),
        standalone.ResolvedDevice("Battery", 1, 0, -50, "Battery"),
        1,
        1.0,
        1.0,
    )
    future = session._loop.create_future()
    future.set_result(b"old")
    session._pending[0x14].append(future)

    session._handle_notification(
        1,
        bytearray(standalone.create_command_frame(0x14, b"new")),
    )

    assert future.result() == b"old"
    assert not session._pending[0x14]


def test_parse_records_can_drop_parser_result() -> None:
    assert standalone._parse_records(b"\x01", 1, lambda chunk: None) == []


def test_runtime_parser_preserves_non_numeric_firmware_build() -> None:
    payload = bytearray(0x68)
    payload[4] = 0xFF
    payload[0x51:0x5D] = b"not-a-date!!"

    result = standalone.parse_runtime_info(payload)

    assert result["work_mode_label"] == "Unknown (255)"
    assert result["firmware_build"] == "not-a-date!!"


def test_bms_parser_skips_out_of_range_cell_voltage() -> None:
    payload = bytearray(80)
    payload[48:50] = (0).to_bytes(2, "little")
    payload[50:52] = (5000).to_bytes(2, "little")
    payload[52:54] = (3300).to_bytes(2, "little")

    result = standalone.parse_bms_data(payload)

    assert result["cell_voltages_v"] == ["3.300"]


def test_meter_ip_all_zero_payload_is_not_configured() -> None:
    assert standalone.parse_meter_ip(bytes(16)) == {
        "ip_address": "Not configured",
        "configured": False,
    }
