"""Unit tests for all original Home Assistant entity platforms."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from bleak.backends.device import BLEDevice

from custom_components.marstek_ble import binary_sensor, button, select, sensor, switch
from custom_components.marstek_ble.const import (
    CMD_AUTO_MODE,
    CMD_CHARGE_MODE,
    CMD_OUTPUT_CONTROL,
    CMD_REBOOT,
    CMD_WORK_MODE,
)
from custom_components.marstek_ble.marstek_device import MarstekData


class FakeDevice:
    def __init__(self, result=True) -> None:
        self.result = result
        self.calls = []

    async def send_command(self, command, payload=b""):
        self.calls.append((command, payload))
        return self.result


def coordinator(data=None, *, result=True):
    ble = BLEDevice("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")
    return SimpleNamespace(
        data=data if data is not None else MarstekData(),
        ble_device=ble,
        device_name="Battery",
        address=ble.address,
        last_update_success=True,
        device=FakeDevice(result),
    )


def entry(coordinator_instance):
    return SimpleNamespace(entry_id="entry-1", runtime_data=coordinator_instance)


@pytest.mark.asyncio
async def test_all_platform_setup_functions_create_expected_entities() -> None:
    coordinator_instance = coordinator()
    config_entry = entry(coordinator_instance)
    created = {}
    for name, module in {
        "sensor": sensor,
        "binary": binary_sensor,
        "button": button,
        "switch": switch,
        "select": select,
    }.items():
        entities = []
        await module.async_setup_entry(None, config_entry, entities.extend)
        created[name] = entities
    assert len(created["sensor"]) == 70
    assert len(created["binary"]) == 5
    assert len(created["button"]) == 5
    assert len(created["switch"]) == 5
    assert len(created["select"]) == 3
    assert {
        entity._key for entity in created["sensor"] if hasattr(entity, "_key")
    } >= {
        "battery_voltage",
        "battery_power",
        "cell_16_voltage",
        "battery_state",
        "meter_ip",
    }


@pytest.mark.known_issue
@pytest.mark.asyncio
async def test_entity_unique_ids_are_unique_across_platforms() -> None:
    coordinator_instance = coordinator()
    config_entry = entry(coordinator_instance)
    all_entities = []
    for module in (sensor, binary_sensor, button, switch, select):
        await module.async_setup_entry(None, config_entry, all_entities.extend)
    unique_ids = [entity._attr_unique_id for entity in all_entities]
    duplicates = sorted(
        {value for value in unique_ids if unique_ids.count(value) > 1}
    )
    assert duplicates == []


def test_numeric_sensor_values_staleness_and_device_info(monkeypatch) -> None:
    data = MarstekData(battery_voltage=50.0, battery_current=-2.0)
    data.mark_field_update("battery_voltage", 0x14, timestamp=900.0)
    data.mark_field_update("battery_current", 0x14, timestamp=950.0)
    coordinator_instance = coordinator(data)
    config_entry = entry(coordinator_instance)
    entity = sensor.MarstekSensor(
        coordinator_instance,
        config_entry,
        "battery_power",
        "Battery Power",
        lambda value: value.battery_voltage * value.battery_current,
        "W",
        "power",
        "measurement",
        stale_fields=["battery_voltage", "battery_current"],
    )
    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.time.time", lambda: 1000.0
    )
    assert entity.native_value == -100.0
    assert entity._stale_age_seconds() == 100.0
    assert entity.available is True
    assert entity._get_representative_metadata()["command_hex"] == "0x14"
    assert entity.device_info["identifiers"] == {
        ("marstek_ble", coordinator_instance.ble_device.address)
    }
    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.time.time", lambda: 1601.0
    )
    assert entity.available is False


def test_sensor_without_metadata_remains_available_and_handles_none_data() -> None:
    coordinator_instance = coordinator(MarstekData())
    config_entry = entry(coordinator_instance)
    entity = sensor.MarstekSensor(
        coordinator_instance,
        config_entry,
        "battery_soc",
        "SOC",
        lambda value: value.battery_soc,
        "%",
        None,
        None,
    )
    assert entity.available is True
    assert entity.native_value is None
    assert entity._stale_age_seconds() is None
    assert entity._get_representative_metadata() is None
    coordinator_instance.data = None
    assert entity.available is False


def test_text_sensor_converts_values_to_strings_and_tracks_staleness(monkeypatch) -> None:
    data = MarstekData(config_mode=2)
    data.mark_field_update("config_mode", 0x1A, timestamp=100.0)
    coordinator_instance = coordinator(data)
    config_entry = entry(coordinator_instance)
    entity = sensor.MarstekTextSensor(
        coordinator_instance,
        config_entry,
        "config_mode",
        "Config Mode",
        lambda value: value.config_mode,
    )
    monkeypatch.setattr(
        "custom_components.marstek_ble.marstek_device.time.time", lambda: 110.0
    )
    assert entity.native_value == "2"
    assert entity.available is True
    data.config_mode = None
    assert entity.native_value is None


def test_binary_sensor_state_availability_and_device_info() -> None:
    data = MarstekData(wifi_connected=True)
    coordinator_instance = coordinator(data)
    config_entry = entry(coordinator_instance)
    entity = binary_sensor.MarstekBinarySensor(
        coordinator_instance,
        config_entry,
        "wifi_connected",
        "WiFi",
        lambda value: value.wifi_connected,
    )
    assert entity.is_on is True
    assert entity.available is True
    coordinator_instance.data = None
    assert entity.available is False
    assert entity.device_info["model"] == "Venus E"


@pytest.mark.asyncio
async def test_button_sends_configured_command_and_payload() -> None:
    coordinator_instance = coordinator()
    entity = button.MarstekButton(
        coordinator_instance,
        entry(coordinator_instance),
        "reboot",
        "Reboot",
        CMD_REBOOT,
        b"",
    )
    await entity.async_press()
    assert coordinator_instance.device.calls == [(CMD_REBOOT, b"")]
    assert entity.device_info["name"] == "Battery"


@pytest.mark.asyncio
async def test_switch_updates_assumed_state_only_after_success() -> None:
    data = MarstekData(out1_active=None)
    coordinator_instance = coordinator(data)
    entity = switch.MarstekSwitch(
        coordinator_instance,
        entry(coordinator_instance),
        "output",
        "Output",
        CMD_OUTPUT_CONTROL,
        lambda value: value.out1_active,
    )
    assert entity.assumed_state is False
    assert entity.is_on is None
    await entity.async_turn_on()
    assert entity.is_on is True
    assert coordinator_instance.device.calls[-1] == (CMD_OUTPUT_CONTROL, b"\x01")
    assert entity._write_count == 1
    coordinator_instance.device.result = False
    await entity.async_turn_off()
    assert entity.is_on is True
    assert entity._write_count == 1
    data.out1_active = False
    entity._handle_coordinator_update()
    assert entity.is_on is False


def test_switch_without_value_function_reports_assumed_state() -> None:
    coordinator_instance = coordinator()
    entity = switch.MarstekSwitch(
        coordinator_instance,
        entry(coordinator_instance),
        "eps",
        "EPS",
        0x05,
        None,
    )
    assert entity.assumed_state is True
    assert entity.is_on is None


@pytest.mark.asyncio
async def test_operating_mode_select_maps_options_and_ignores_invalid_option() -> None:
    coordinator_instance = coordinator()
    entity = select.MarstekOperatingModeSelect(
        coordinator_instance, entry(coordinator_instance)
    )
    assert entity.current_option is None
    await entity.async_select_option("Self-Consumption")
    assert coordinator_instance.device.calls[-1] == (CMD_AUTO_MODE, b"\x01")
    assert entity.current_option == "Self-Consumption"
    await entity.async_select_option("Manual")
    assert coordinator_instance.device.calls[-1] == (CMD_WORK_MODE, b"\x01")
    assert entity.current_option == "Manual"
    call_count = len(coordinator_instance.device.calls)
    await entity.async_select_option("Unsupported")
    assert len(coordinator_instance.device.calls) == call_count


@pytest.mark.asyncio
async def test_generic_select_syncs_and_updates_on_success() -> None:
    data = MarstekData(config_mode=1)
    coordinator_instance = coordinator(data)
    entity = select.MarstekSelect(
        coordinator_instance,
        entry(coordinator_instance),
        "charge_mode",
        "Charge Mode",
        CMD_CHARGE_MODE,
        {"A": (b"\x00", 0), "B": (b"\x01", 1)},
        lambda value: value.config_mode,
    )
    assert entity.current_option == "B"
    await entity.async_select_option("A")
    assert entity.current_option == "A"
    assert coordinator_instance.device.calls == [(CMD_CHARGE_MODE, b"\x00")]
    data.config_mode = 1
    entity._handle_coordinator_update()
    assert entity.current_option == "B"
    coordinator_instance.device.result = False
    await entity.async_select_option("A")
    assert entity.current_option == "B"
