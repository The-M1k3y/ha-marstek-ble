"""Second-pass coverage tests for product runtime and entity edge paths."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from bleak.backends.device import BLEDevice

from custom_components.marstek_ble.const import CMD_OUTPUT_CONTROL
from custom_components.marstek_ble.entity import ProductDeviceSpec, ProductProfile
from custom_components.marstek_ble.marstek_device import MarstekData
from custom_components.marstek_ble.product_runtime import ProductProtocol, ProductRuntime
from custom_components.marstek_ble.products import VENUS_PROFILE, VENUS_RUNTIME, VenusData
from custom_components.marstek_ble import select, sensor, switch


class FakeDevice:
    """Minimal command target for entity tests."""

    def __init__(self, result: bool) -> None:
        self.result = result
        self.calls: list[tuple[int, bytes]] = []

    async def send_command(self, command: int, payload: bytes = b"") -> bool:
        self.calls.append((command, payload))
        return self.result


def _coordinator(data=None, *, result: bool = True) -> SimpleNamespace:
    ble = BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")
    return SimpleNamespace(
        data=data if data is not None else MarstekData(),
        ble_device=ble,
        device_name="Battery",
        address=ble.address,
        last_update_success=True,
        device=FakeDevice(result),
    )


def _entry() -> SimpleNamespace:
    return SimpleNamespace(entry_id="entry-1")


def test_tracked_product_data_empty_path_and_implicit_timestamp(monkeypatch) -> None:
    data = VenusData()
    assert data._metadata_aliases(()) == ()

    monkeypatch.setattr(
        "custom_components.marstek_ble.product_runtime.time.time",
        lambda: 123.0,
    )
    data.mark_field_update("runtime.out1_power", 0x03)

    metadata = data.get_field_metadata("runtime.out1_power")
    assert metadata is not None
    assert metadata["timestamp"] == "1970-01-01T00:02:03+00:00"
    assert metadata["age_seconds"] == 0.0
    assert metadata["payload_hex"] is None


def test_product_runtime_rejects_invalid_custom_parser_commands() -> None:
    with pytest.raises(ValueError, match="fit in one byte"):
        ProductRuntime(
            profile=VENUS_PROFILE,
            fast_poll=(),
            payload_parsers={-1: lambda payload, data: ()},
        )

    with pytest.raises(ValueError, match="fit in one byte"):
        ProductRuntime(
            profile=VENUS_PROFILE,
            fast_poll=(),
            payload_parsers={0x100: lambda payload, data: ()},
        )


@dataclass
class ParserOnlyData:
    """Data model intentionally lacking field-update metadata support."""

    value: bytes = b""


def _parser_only_runtime(parser=None) -> ProductRuntime:
    profile = ProductProfile(
        product_id="parser-only",
        device=ProductDeviceSpec("Marstek", "Parser Only"),
        data_type=ParserOnlyData,
        packets=(),
    )

    def default_parser(payload: bytes, data: ParserOnlyData):
        data.value = payload
        return (("value",),)

    return ProductRuntime(
        profile=profile,
        fast_poll=(),
        payload_parsers={0x42: parser or default_parser},
    )


def test_product_runtime_supports_parser_without_packet_schema() -> None:
    runtime = _parser_only_runtime()
    data = ParserOnlyData()

    assert runtime.parse_payload(0x42, b"abc", data) == (("value",),)
    assert data.value == b"abc"
    assert runtime.parse_payload(0x43, b"ignored", data) is None


def test_product_protocol_accepts_data_without_metadata_marker() -> None:
    runtime = _parser_only_runtime()
    protocol = ProductProtocol(runtime)
    data = ParserOnlyData()

    assert protocol.parse_notification(protocol.build_command(0x42, b"abc"), data)
    assert data.value == b"abc"


def test_product_protocol_rejects_invalid_header_and_declared_length() -> None:
    protocol = ProductProtocol(VENUS_RUNTIME)
    data = VenusData()

    invalid_header = bytearray(protocol.build_command(0x03, bytes(37)))
    invalid_header[0] = 0x72
    assert protocol.parse_notification(bytes(invalid_header), data) is False

    invalid_marker = bytearray(protocol.build_command(0x03, bytes(37)))
    invalid_marker[2] = 0x22
    assert protocol.parse_notification(bytes(invalid_marker), data) is False

    invalid_length = bytearray(protocol.build_command(0x03, bytes(37)))
    invalid_length[1] += 1
    assert protocol.parse_notification(bytes(invalid_length), data) is False


def test_product_protocol_contains_payload_parser_exception() -> None:
    def explode(payload: bytes, data: ParserOnlyData):
        raise RuntimeError("parser failed")

    runtime = _parser_only_runtime(explode)
    protocol = ProductProtocol(runtime)

    assert (
        protocol.parse_notification(
            protocol.build_command(0x42, b"abc"), ParserOnlyData()
        )
        is False
    )


def test_venus_custom_parsers_ignore_malformed_and_unknown_fields() -> None:
    protocol = ProductProtocol(VENUS_RUNTIME)
    data = VenusData()

    assert protocol.parse_notification(
        protocol.build_command(
            0x04,
            b"malformed,unknown=value,type= Venus ,also-malformed",
        ),
        data,
    )
    assert data.device.device_type == "Venus"

    assert protocol.parse_notification(
        protocol.build_command(
            0x24,
            b"malformed,unknown:value,ip:192.0.2.10,also-malformed",
        ),
        data,
    )
    assert data.network.ip_address == "192.0.2.10"
    assert data.network.gateway is None


def test_venus_derived_entities_cover_missing_positive_and_negative_values() -> None:
    data = VenusData()
    bindings = {
        binding.description.key: binding
        for binding in VENUS_PROFILE.build_entity_plan(data).entities
    }

    for key in (
        "battery_power",
        "battery_power_in",
        "battery_power_out",
        "remaining_capacity",
        "available_capacity",
    ):
        assert bindings[key].value_from(data) is None

    data.battery.battery_voltage = 50.0
    data.battery.battery_current = -2.0
    data.battery.battery_soc = 25.0
    data.battery.design_capacity = 1000.0

    assert bindings["battery_power"].value_from(data) == -100.0
    assert bindings["battery_power_in"].value_from(data) == 0
    assert bindings["battery_power_out"].value_from(data) == 100.0
    assert bindings["remaining_capacity"].value_from(data) == 250.0
    assert bindings["available_capacity"].value_from(data) == 750.0

    data.battery.battery_current = 2.0
    assert bindings["battery_power_in"].value_from(data) == 100.0
    assert bindings["battery_power_out"].value_from(data) == 0


def test_numeric_sensor_metadata_helpers_handle_data_becoming_none() -> None:
    coordinator = _coordinator(MarstekData())
    entity = sensor.MarstekSensor(
        coordinator,
        _entry(),
        "battery_soc",
        "SOC",
        lambda value: value.battery_soc,
        "%",
        None,
        None,
    )

    coordinator.data = None
    assert entity._stale_age_seconds() is None
    assert entity._get_representative_metadata() is None


@pytest.mark.asyncio
async def test_operating_mode_select_preserves_state_when_command_fails() -> None:
    coordinator = _coordinator(result=False)
    entity = select.MarstekOperatingModeSelect(coordinator, _entry())

    await entity.async_select_option("Manual")

    assert coordinator.device.calls
    assert entity.current_option is None
    assert entity._write_count == 0


def test_generic_select_sync_handles_absent_none_and_unknown_values() -> None:
    coordinator = _coordinator(MarstekData(config_mode=None))

    without_reader = select.MarstekSelect(
        coordinator,
        _entry(),
        "without_reader",
        "Without Reader",
        0x01,
        {"A": (b"\x00", 0)},
        None,
    )
    assert without_reader.current_option is None

    with_reader = select.MarstekSelect(
        coordinator,
        _entry(),
        "with_reader",
        "With Reader",
        0x01,
        {"A": (b"\x00", 0)},
        lambda value: value.config_mode,
    )
    assert with_reader.current_option is None

    coordinator.data.config_mode = 99
    with_reader._handle_coordinator_update()
    assert with_reader.current_option is None


@pytest.mark.asyncio
async def test_switch_failed_turn_on_and_successful_turn_off_paths() -> None:
    coordinator = _coordinator(result=False)
    entity = switch.MarstekSwitch(
        coordinator,
        _entry(),
        "output",
        "Output",
        CMD_OUTPUT_CONTROL,
        None,
    )

    await entity.async_turn_on()
    assert entity.is_on is None
    assert entity._write_count == 0

    coordinator.device.result = True
    await entity.async_turn_off()
    assert entity.is_on is False
    assert entity._write_count == 1
    assert coordinator.device.calls[-1] == (CMD_OUTPUT_CONTROL, b"\x00")
