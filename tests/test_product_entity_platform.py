"""Tests for runtime declarative entity-platform synchronization."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.marstek_ble.entity import EntityPlatform
from custom_components.marstek_ble.product_entity_platform import (
    ProductEntityManager,
    setup_product_entity_platform,
)
from custom_components.marstek_ble.products import JUPITER_RUNTIME


def _factory(_coordinator, _entry, binding):
    return binding


def test_entity_manager_adds_jupiter_battery_children_only_when_present() -> None:
    data = JUPITER_RUNTIME.create_data()
    coordinator = SimpleNamespace(
        data=data,
        product=JUPITER_RUNTIME,
    )
    batches: list[list] = []
    manager = ProductEntityManager(
        coordinator,
        SimpleNamespace(),
        lambda entities: batches.append(list(entities)),
        EntityPlatform.SENSOR,
        _factory,
    )

    manager.sync()
    initial = [binding for batch in batches for binding in batch]
    assert initial
    assert not any(binding.device.key.startswith("battery_pack_") for binding in initial)
    assert any(binding.unique_key == "pv_inputs_0_power" for binding in initial)
    assert any(binding.unique_key == "pv_inputs_3_power" for binding in initial)

    batches.clear()
    data.battery.pack_count = 2
    manager.sync()
    added = [binding for batch in batches for binding in batch]
    assert {binding.device.key for binding in added} == {
        "battery_pack_0",
        "battery_pack_1",
    }
    assert len(added) == 10

    second_pack_binding = next(
        binding for binding in added if binding.device.key == "battery_pack_1"
    )
    assert second_pack_binding.is_present(data) is True

    batches.clear()
    manager.sync()
    assert batches == []

    data.battery.pack_count = 1
    assert second_pack_binding.is_present(data) is False
    manager.sync()
    assert batches == []

    data.battery.pack_count = 3
    manager.sync()
    added = [binding for batch in batches for binding in batch]
    assert {binding.device.key for binding in added} == {"battery_pack_2"}
    assert len(added) == 5


def test_entity_manager_does_nothing_until_data_exists() -> None:
    coordinator = SimpleNamespace(data=None, product=JUPITER_RUNTIME)
    batches: list[list] = []
    manager = ProductEntityManager(
        coordinator,
        SimpleNamespace(),
        lambda entities: batches.append(list(entities)),
        EntityPlatform.SENSOR,
        _factory,
    )

    manager.sync()
    assert batches == []


def test_entity_manager_retries_entities_after_add_failure() -> None:
    data = JUPITER_RUNTIME.create_data()
    coordinator = SimpleNamespace(data=data, product=JUPITER_RUNTIME)
    calls = 0

    def failing_add(_entities):
        nonlocal calls
        calls += 1
        raise RuntimeError("add failed")

    manager = ProductEntityManager(
        coordinator,
        SimpleNamespace(),
        failing_add,
        EntityPlatform.BINARY_SENSOR,
        _factory,
    )

    with pytest.raises(RuntimeError, match="add failed"):
        manager.sync()
    with pytest.raises(RuntimeError, match="add failed"):
        manager.sync()
    assert calls == 2


def test_setup_product_entity_platform_subscribes_and_populates_immediately() -> None:
    data = JUPITER_RUNTIME.create_data()
    listeners = []
    unloaded = []

    def async_add_listener(callback):
        listeners.append(callback)
        return lambda: listeners.remove(callback)

    coordinator = SimpleNamespace(
        data=data,
        product=JUPITER_RUNTIME,
        async_add_listener=async_add_listener,
    )
    entry = SimpleNamespace(async_on_unload=lambda callback: unloaded.append(callback))
    batches: list[list] = []

    manager = setup_product_entity_platform(
        coordinator,
        entry,
        lambda entities: batches.append(list(entities)),
        EntityPlatform.BINARY_SENSOR,
        _factory,
    )

    assert isinstance(manager, ProductEntityManager)
    assert len(listeners) == 1
    assert len(unloaded) == 1
    assert batches
    initial_keys = {
        binding.unique_key
        for batch in batches
        for binding in batch
    }
    assert "ac_output_active" in initial_keys
    assert "pv_inputs_0_connected" in initial_keys
    assert "pv_inputs_3_connected" in initial_keys

    batches.clear()
    listeners[0]()
    assert batches == []
