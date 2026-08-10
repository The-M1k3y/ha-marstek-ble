"""Entity-contract coverage for unverified Jupiter diagnostic fields."""

from __future__ import annotations

import struct

from homeassistant.helpers.entity import EntityCategory

from custom_components.marstek_ble.products.jupiter import (
    JUPITER_PROFILE,
    JupiterData,
    JupiterPackets,
)
from custom_components.marstek_ble.schema import parse_into


def test_unverified_jupiter_fields_are_diagnostic_entities() -> None:
    data = JupiterData()
    data.battery.pack_count = 1
    plan = JUPITER_PROFILE.build_entity_plan(data)
    entities = {entity.unique_key: entity for entity in plan.entities}

    expected_diagnostics = {
        "operational_status",
        "daily_pv_generation",
        "monthly_pv_generation",
        "local_total_discharge_energy",
        "inverter_state_flags",
        "inverter_error_code",
        "inverter_warning_code",
        "grid_voltage",
        "grid_power_factor",
        "bus_voltage",
        "inverter_temperature",
        "mppt_state_flags",
        "mppt_error_code",
        "mppt_temperature",
        "mppt_warning_code",
        "mppt_dc_output_voltage",
        "mppt_dc_output_current",
        "base_voltage",
        "pe_voltage",
        "charge_voltage_limit",
        "discharge_current_limit",
        "battery_soh",
        "battery_temperature",
        "bms_error_code_1",
        "bms_warning_code_1",
        "bms_error_code_2",
        "bms_warning_code_2",
        "cell_flags",
        "bms_status_flags",
        "battery_pack_count",
        "battery_temp_sensor_1",
        "battery_temp_sensor_2",
        "battery_temp_sensor_3",
        "battery_temp_sensor_4",
        "bms_environment_temperature",
        "bms_mosfet_temperature",
        "battery_pack_0_highest_cell_index",
        "battery_pack_0_lowest_cell_index",
        "battery_pack_0_highest_cell_voltage",
        "battery_pack_0_lowest_cell_voltage",
        "battery_pack_0_status",
    }

    assert expected_diagnostics <= entities.keys()
    assert all(
        entities[key].description.entity_category is EntityCategory.DIAGNOSTIC
        for key in expected_diagnostics
    )


def test_event_history_fields_are_exposed_as_diagnostics() -> None:
    data = JupiterData()
    plan = JUPITER_PROFILE.build_entity_plan(data)
    entities = {entity.unique_key: entity for entity in plan.entities}

    for index in range(20):
        prefix = f"events_{index}"
        for key in ("year", "month", "day", "hour", "minute", "event_value", "event_state"):
            entity = entities[f"{prefix}_{key}"]
            assert entity.description.entity_category is EntityCategory.DIAGNOSTIC
            assert entity.description.name.startswith(f"Event {index + 1} ")


def test_tentative_base_and_pe_voltages_parse_with_diagnostic_entities() -> None:
    data = JupiterData()
    payload = bytearray(166)
    payload[0x54:0x56] = struct.pack("<H", 523)
    payload[0x56:0x58] = struct.pack("<H", 17)

    parse_into(payload, JupiterPackets.DETAILED_TELEMETRY, data)

    assert data.battery.base_voltage == 52.3
    assert data.battery.pe_voltage == 1.7

    plan = JUPITER_PROFILE.build_entity_plan(data)
    entities = {entity.unique_key: entity for entity in plan.entities}
    assert entities["base_voltage"].value_from(data) == 52.3
    assert entities["pe_voltage"].value_from(data) == 1.7
    assert entities["base_voltage"].description.entity_category is EntityCategory.DIAGNOSTIC
    assert entities["pe_voltage"].description.entity_category is EntityCategory.DIAGNOSTIC


def test_fields_without_a_current_interpretation_remain_unexposed() -> None:
    data = JupiterData()
    plan = JUPITER_PROFILE.build_entity_plan(data)
    keys = {entity.description.key for entity in plan.entities}

    assert "grid_current" not in keys
    assert "status_21" not in keys
    assert "status_22" not in keys
    assert "status_24" not in keys
