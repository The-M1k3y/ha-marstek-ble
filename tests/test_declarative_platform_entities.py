"""Tests for live entities created from declarative product bindings."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.marstek_ble.binary_sensor import MarstekBinarySensor
from custom_components.marstek_ble.entity import EntityPlatform
from custom_components.marstek_ble.products import JUPITER_RUNTIME
from custom_components.marstek_ble.sensor import MarstekSensor


def _coordinator(data):
    return SimpleNamespace(
        data=data,
        last_update_success=True,
        address="AA:BB:CC:DD:EE:FF",
        ble_device=SimpleNamespace(address="AA:BB:CC:DD:EE:FF"),
        device_name="Jupiter Test",
        product=JUPITER_RUNTIME,
    )


def _entry():
    return SimpleNamespace(entry_id="entry")


def test_jupiter_sensor_binding_uses_product_value_and_main_device_metadata() -> None:
    data = JUPITER_RUNTIME.create_data()
    data.pv_inputs[0].power = 321.5
    plan = JUPITER_RUNTIME.profile.build_entity_plan(data)
    binding = next(
        item
        for item in plan.entities
        if item.platform is EntityPlatform.SENSOR
        and item.unique_key == "pv_inputs_0_power"
    )

    entity = MarstekSensor(_coordinator(data), _entry(), binding)

    assert entity.native_value == pytest.approx(321.5)
    assert entity._attr_unique_id == "entry_pv_inputs_0_power"
    assert entity.available is True
    assert entity.device_info["identifiers"] == {
        ("marstek_ble", "AA:BB:CC:DD:EE:FF")
    }
    assert entity.device_info["model"] == "Jupiter-C Plus"


def test_jupiter_child_sensor_has_stable_child_identifier_and_runtime_presence() -> None:
    data = JUPITER_RUNTIME.create_data()
    data.battery.pack_count = 2
    data.battery.packs[1].highest_cell_voltage = 3.456
    plan = JUPITER_RUNTIME.profile.build_entity_plan(data)
    binding = next(
        item
        for item in plan.entities
        if item.platform is EntityPlatform.SENSOR
        and item.device.key == "battery_pack_1"
        and item.description.key == "highest_cell_voltage"
    )

    entity = MarstekSensor(_coordinator(data), _entry(), binding)

    assert entity.native_value == pytest.approx(3.456)
    assert entity.available is True
    assert entity.device_info["name"] == "Expansion Battery 1"
    assert entity.device_info["identifiers"] == {
        ("marstek_ble", "AA:BB:CC:DD:EE:FF:battery_pack:1")
    }
    assert entity.device_info["via_device"] == (
        "marstek_ble",
        "AA:BB:CC:DD:EE:FF",
    )

    data.battery.pack_count = 1
    assert entity.available is False


def test_jupiter_binary_sensor_binding_uses_declarative_presence_value() -> None:
    data = JUPITER_RUNTIME.create_data()
    data.pv_inputs[3].connected = True
    plan = JUPITER_RUNTIME.profile.build_entity_plan(data)
    binding = next(
        item
        for item in plan.entities
        if item.platform is EntityPlatform.BINARY_SENSOR
        and item.unique_key == "pv_inputs_3_connected"
    )

    entity = MarstekBinarySensor(_coordinator(data), _entry(), binding)

    assert entity.is_on is True
    assert entity.available is True
    assert entity._attr_unique_id == "entry_pv_inputs_3_connected"
    assert entity.device_info["model"] == "Jupiter-C Plus"


def test_legacy_sensor_constructor_remains_supported() -> None:
    data = JUPITER_RUNTIME.create_data()
    data.runtime.battery_soc = 42
    coordinator = _coordinator(data)

    entity = MarstekSensor(
        coordinator,
        _entry(),
        "legacy_soc",
        "Legacy SOC",
        lambda value: value.runtime.battery_soc,
        "%",
        None,
        None,
    )

    assert entity.native_value == 42
    assert entity._attr_unique_id == "entry_legacy_soc"
