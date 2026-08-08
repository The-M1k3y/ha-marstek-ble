"""Coverage-focused tests for declarative schemas, entity plans, and Jupiter."""

from __future__ import annotations

import struct
from dataclasses import dataclass, fields

import pytest
from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription

# The isolated Home Assistant test stub predates the Jupiter frequency sensor.
# Keep this compatibility shim local to the test until the stub grows the class.
if not hasattr(SensorDeviceClass, "FREQUENCY"):
    SensorDeviceClass.FREQUENCY = "frequency"

from custom_components.marstek_ble.entity import (  # noqa: E402
    DeviceBinding,
    EntityBinding,
    EntityPlatform,
    ProductDeviceSpec,
    ProductProfile,
    binary_sensor_entity,
    derived_binary_sensor,
    derived_sensor,
    indexed_sensor_entities,
    sensor_entity,
)
from custom_components.marstek_ble.products.jupiter import (  # noqa: E402
    JUPITER_PROFILE,
    JupiterData,
    JupiterPackets,
    _battery_power,
)
from custom_components.marstek_ble.schema import (  # noqa: E402
    FieldSource,
    PacketSchema,
    RepeatedSectionSource,
    RepeatedSectionSpec,
    SectionSource,
    bit,
    bits,
    divide_by,
    divide_each_by,
    get_field_entities,
    get_field_sources,
    get_indexed_entities,
    get_repeated_section,
    get_section_sources,
    identity,
    iter_parsed_fields,
    multiply_by,
    nonzero,
    parse_into,
    repeated_section_field,
    section_field,
    source_field,
    value_field,
)


def test_packet_schema_validation_and_payload_bounds() -> None:
    with pytest.raises(ValueError, match="name cannot be empty"):
        PacketSchema("", 1)
    with pytest.raises(ValueError, match="fit in one byte"):
        PacketSchema("bad", -1)
    with pytest.raises(ValueError, match="fit in one byte"):
        PacketSchema("bad", 0x100)
    with pytest.raises(ValueError, match="cannot be negative"):
        PacketSchema("bad", 1, -1)
    with pytest.raises(ValueError, match="cannot be smaller"):
        PacketSchema("bad", 1, 4, 3)

    packet = PacketSchema("bounded", 1, 2, 3)
    packet.validate_payload(b"12")
    packet.validate_payload(b"123")
    with pytest.raises(ValueError, match="too short"):
        packet.validate_payload(b"1")
    with pytest.raises(ValueError, match="too long"):
        packet.validate_payload(b"1234")


def test_field_source_validation_length_gates_and_tuple_parsing() -> None:
    with pytest.raises(ValueError, match="offset cannot be negative"):
        FieldSource(-1, "<B")
    with pytest.raises(ValueError, match="byte order explicitly"):
        FieldSource(0, "B")
    with pytest.raises(ValueError, match="Invalid struct format"):
        FieldSource(0, "<Z")
    with pytest.raises(ValueError, match="minimum length cannot be negative"):
        FieldSource(0, "<B", minimum_length=-1)
    with pytest.raises(ValueError, match="cannot end before"):
        FieldSource(2, "<H", maximum_length=3)
    with pytest.raises(ValueError, match="cannot be smaller"):
        FieldSource(0, "<B", minimum_length=4, maximum_length=3)

    source = FieldSource(
        1,
        "<H",
        lambda value: value / 10,
        minimum_length=4,
        maximum_length=5,
    )
    assert source.size == 2
    assert source.end_offset == 3
    assert source.applies_to(3) is False
    assert source.applies_to(4) is True
    assert source.applies_to(6) is False
    assert source.applies_to(4, base_offset=1) is True
    assert source.parse_from(b"\x00\xd2\x04\x00") == (1234, 123.4)
    with pytest.raises(ValueError, match="exceeds payload length"):
        source.parse_from(b"\x00\x01")

    tuple_source = FieldSource(0, "<BB", lambda value: sum(value))
    assert tuple_source.parse_from(b"\x02\x03") == ((2, 3), 5)


def test_section_and_repeated_section_validation() -> None:
    packet = PacketSchema("packet", 1)
    with pytest.raises(ValueError, match="offset cannot be negative"):
        SectionSource(-1)
    with pytest.raises(ValueError, match="offset cannot be negative"):
        RepeatedSectionSource(-1, 1)
    with pytest.raises(ValueError, match="stride must be positive"):
        RepeatedSectionSource(0, 0)
    with pytest.raises(ValueError, match="count must be positive"):
        RepeatedSectionSpec(lambda: object(), 0, {packet: RepeatedSectionSource(0, 1)})
    with pytest.raises(ValueError, match="requires at least one"):
        RepeatedSectionSpec(lambda: object(), 1, {})

    spec = RepeatedSectionSpec(
        lambda: object(),
        1,
        {packet: RepeatedSectionSource(2, 3)},
    )
    assert spec.sources[packet] == RepeatedSectionSource(2, 3)
    with pytest.raises(TypeError):
        spec.sources[packet] = RepeatedSectionSource(0, 1)  # type: ignore[index]


def test_field_builders_and_metadata_accessors() -> None:
    packet = PacketSchema("packet", 1)
    direct = sensor_entity(key="direct", name="Direct")
    indexed = indexed_sensor_entities(
        2,
        lambda index: SensorEntityDescription(key=f"value_{index}", name=f"Value {index}"),
    )

    with pytest.raises(ValueError, match="requires at least one"):
        source_field(sources={})
    with pytest.raises(ValueError, match="requires entity metadata"):
        value_field(entities=())
    with pytest.raises(ValueError, match="cannot be empty"):
        section_field(dict, sources={})

    @dataclass(slots=True)
    class Child:
        value: int | None = source_field(
            sources={packet: FieldSource(0, "<B")},
            entities=(direct,),
        )

    @dataclass(slots=True)
    class Model:
        child: Child = section_field(Child, sources={packet: SectionSource(1)})
        items: list[Child] = repeated_section_field(
            Child,
            count=2,
            sources={packet: RepeatedSectionSource(2, 1)},
        )
        values: list[int] = value_field(
            entities=(),
            indexed_entities=(indexed,),
            default_factory=lambda: [10, 20],
            repr=False,
        )
        cache: list[int] = source_field(
            sources={packet: FieldSource(0, "<B")},
            default_factory=list,
            repr=False,
        )

    model_fields = {item.name: item for item in fields(Model)}
    child_field = fields(Child)[0]
    assert get_field_sources(child_field)[packet].offset == 0
    assert get_field_entities(child_field) == (direct,)
    assert get_section_sources(model_fields["child"])[packet].offset == 1
    assert get_repeated_section(model_fields["items"]).count == 2
    assert get_indexed_entities(model_fields["values"]) == (indexed,)
    assert Model().values == [10, 20]
    assert Model().cache == []


def test_nested_parsing_repeated_records_and_atomic_failure() -> None:
    packet = PacketSchema("nested", 0x31, 4, 4)

    @dataclass(slots=True)
    class Child:
        value: int | None = source_field(sources={packet: FieldSource(0, "<B")})

    @dataclass(slots=True)
    class Model:
        child: Child = section_field(Child, sources={packet: SectionSource(1)})
        items: list[Child] = repeated_section_field(
            Child,
            count=2,
            sources={packet: RepeatedSectionSource(2, 1)},
        )

    data = Model()
    updates = tuple(iter_parsed_fields(b"\x00\x11\x22\x33", packet, data))
    assert [update.path_string for update in updates] == [
        "child.value",
        "items.0.value",
        "items.1.value",
    ]
    assert [update.raw_value for update in updates] == [0x11, 0x22, 0x33]
    assert data.child.value is None
    assert parse_into(b"\x00\x11\x22\x33", packet, data) is data
    assert data.child.value == 0x11
    assert [item.value for item in data.items] == [0x22, 0x33]

    with pytest.raises(TypeError, match="dataclass instance"):
        tuple(iter_parsed_fields(b"", PacketSchema("empty", 1), object()))

    data.items = []  # type: ignore[assignment]
    with pytest.raises(ValueError, match="contains 0 items, expected 2"):
        tuple(iter_parsed_fields(b"\x00\x11\x22\x33", packet, data))

    data.items = None  # type: ignore[assignment]
    with pytest.raises(TypeError, match="must contain a list"):
        tuple(iter_parsed_fields(b"\x00\x11\x22\x33", packet, data))

    data.items = [Child(), object()]  # type: ignore[list-item]
    with pytest.raises(TypeError, match="items must be dataclass instances"):
        tuple(iter_parsed_fields(b"\x00\x11\x22\x33", packet, data))

    atomic_packet = PacketSchema("atomic", 0x32, 2, 2)

    def fail_converter(value: int) -> int:
        raise RuntimeError(f"cannot convert {value}")

    @dataclass(slots=True)
    class Atomic:
        first: int = source_field(
            sources={atomic_packet: FieldSource(0, "<B")},
            default=9,
        )
        second: int = source_field(
            sources={atomic_packet: FieldSource(1, "<B", fail_converter)},
            default=8,
        )

    atomic = Atomic()
    with pytest.raises(RuntimeError, match="cannot convert"):
        parse_into(b"\x01\x02", atomic_packet, atomic)
    assert (atomic.first, atomic.second) == (9, 8)


def test_schema_converters_cover_boundaries() -> None:
    marker = object()
    assert identity(marker) is marker
    assert nonzero(0) is False
    assert nonzero(-1) is True
    assert bit(3)(0b1000) is True
    assert bit(3)(0b0100) is False
    assert bits(2, 3)(0b111100) == 0b111
    assert multiply_by(2.5)(4) == 10.0
    assert divide_by(4)(10) == 2.5
    assert divide_each_by(4)([4, 10]) == [1.0, 2.5]

    with pytest.raises(ValueError, match="cannot be negative"):
        bit(-1)
    with pytest.raises(ValueError, match="cannot be negative"):
        bits(-1, 1)
    with pytest.raises(ValueError, match="must be positive"):
        bits(0, 0)
    with pytest.raises(ValueError, match="cannot be zero"):
        divide_by(0)
    with pytest.raises(ValueError, match="cannot be zero"):
        divide_each_by(0)


def test_entity_plan_helpers_presence_and_error_paths() -> None:
    packet = PacketSchema("plan", 0x40)

    @dataclass(slots=True)
    class Item:
        reading: int | None = value_field(
            entities=(sensor_entity(key="reading", name="Reading"),)
        )
        unnamed: int | None = value_field(
            entities=(sensor_entity(key="unnamed", name=None),)
        )

    @dataclass(slots=True)
    class PlanData:
        count: int | None = None
        nested: Item = section_field(Item)
        values: list[int] = value_field(
            entities=(),
            indexed_entities=(
                indexed_sensor_entities(
                    2,
                    lambda index: SensorEntityDescription(
                        key=f"value_{index}",
                        name=f"Value {index}",
                    ),
                ),
            ),
            default_factory=lambda: [1, 2],
        )
        items: list[Item] = repeated_section_field(
            Item,
            count=2,
            sources={packet: RepeatedSectionSource(0, 1)},
            active_count_attribute="count",
            item_name_factory=lambda index: f"Item {index + 1}",
        )

    profile = ProductProfile(
        product_id="plan",
        device=ProductDeviceSpec("Marstek", "Test", "T"),
        data_type=PlanData,
        packets=(packet,),
        derived_entities=(
            derived_sensor(
                description=SensorEntityDescription(key="derived", name="Derived"),
                value_fn=lambda data: data.values[0] + data.values[1],
                stale_paths=(("values",),),
            ),
            derived_binary_sensor(
                description=BinarySensorEntityDescription(key="flag", name="Flag"),
                value_fn=lambda data: bool(data.count),
            ),
        ),
    )

    with pytest.raises(TypeError, match="expects PlanData"):
        profile.build_entity_plan(object())

    data = profile.create_data()
    assert isinstance(data, PlanData)
    data.count = 2
    plan = profile.build_entity_plan(data, configured_repeated_counts={"items": 1})
    assert len(plan.devices) == 1
    assert plan.repeated_counts["items"] == 1
    with pytest.raises(TypeError):
        plan.repeated_counts["items"] = 2  # type: ignore[index]

    repeated_reading = next(
        entity
        for entity in plan.entities
        if entity.path == ("items", 0, "reading")
    )
    assert repeated_reading.description.name == "Item 1 Reading"
    assert repeated_reading.is_present(data) is True
    assert repeated_reading.value_from(data) is None

    indexed = next(entity for entity in plan.entities if entity.path == ("values", 0))
    assert indexed.unique_key == "values_0_value_0"
    assert indexed.value_from(data) == 1

    derived = next(entity for entity in plan.entities if entity.description.key == "derived")
    assert derived.value_from(data) == 3
    assert derived.stale_paths == (("values",),)

    data.count = 2
    changes = profile.detect_expansion_increases(data, plan)
    assert len(changes) == 1
    assert changes[0].path == ("items",)
    assert changes[0].configured_count == 1
    assert changes[0].discovered_count == 2
    assert changes[0].maximum_count == 2
    assert changes[0].issue_id == "plan_items_expansion_count_increased"

    data.count = -5
    assert profile.build_entity_plan(data).repeated_counts["items"] == 0
    data.count = 99
    assert profile.build_entity_plan(data).repeated_counts["items"] == 2

    data.values = [1]
    with pytest.raises(ValueError, match="fewer items than configured"):
        profile.build_entity_plan(data)

    main = DeviceBinding("main", None, "Marstek", "Test")
    assert main.identifier("device") == "device"
    child = DeviceBinding(
        "child",
        "Child",
        "Marstek",
        "Expansion",
        identifier_suffix="slot:1",
    )
    assert child.identifier("device") == "device:slot:1"

    binding = EntityBinding(
        EntityPlatform.SENSOR,
        SensorEntityDescription(key="orphan", name="Orphan"),
        main,
    )
    with pytest.raises(ValueError, match="no value source"):
        binding.value_from(data)


def test_entity_plan_rejects_invalid_child_device_metadata() -> None:
    packet = PacketSchema("bad-child", 0x41)

    @dataclass(slots=True)
    class Item:
        reading: int | None = value_field(
            entities=(sensor_entity(key="reading", name="Reading"),)
        )

    @dataclass(slots=True)
    class Model:
        items: list[Item] = repeated_section_field(
            Item,
            count=1,
            sources={packet: RepeatedSectionSource(0, 1)},
            child_device=object(),
        )

    profile = ProductProfile(
        "bad-child",
        ProductDeviceSpec("Marstek", "Test"),
        Model,
        (packet,),
    )
    with pytest.raises(TypeError, match="RepeatedChildDeviceSpec"):
        profile.build_entity_plan(Model())


def test_jupiter_profile_packet_contract_and_empty_data_shape() -> None:
    data = JUPITER_PROFILE.create_data()
    assert isinstance(data, JupiterData)
    assert JUPITER_PROFILE.product_id == "jupiter_c_plus"
    assert JUPITER_PROFILE.discovery_prefixes == ("MST_JPLS_",)
    assert JUPITER_PROFILE.device.manufacturer == "Marstek"
    assert JUPITER_PROFILE.device.model == "Jupiter-C Plus"
    assert len(data.pv_inputs) == 4
    assert len(data.battery.packs) == 4
    assert len(data.events) == 20

    packets = {packet.command: packet for packet in JUPITER_PROFILE.packets}
    assert packets[0x03] is JupiterPackets.RUNTIME_INFORMATION
    assert packets[0x13] is JupiterPackets.EVENT_HISTORY
    assert packets[0x14] is JupiterPackets.DETAILED_TELEMETRY
    assert packets[0x03].minimum_length == packets[0x03].maximum_length == 74
    assert packets[0x13].minimum_length == packets[0x13].maximum_length == 160
    assert packets[0x14].minimum_length == packets[0x14].maximum_length == 166


def test_jupiter_runtime_packet_parses_summary_and_four_pv_inputs() -> None:
    data = JupiterData()
    payload = bytearray(74)
    for index, (power, connected) in enumerate(
        ((101, 1), (202, 0), (303, 1), (404, 1))
    ):
        offset = index * 3
        payload[offset : offset + 2] = struct.pack("<H", power)
        payload[offset + 2] = connected

    payload[0x0C:0x0E] = struct.pack("<H", 750)
    payload[0x0E] = 1
    payload[0x12] = 1
    payload[0x13:0x15] = struct.pack("<H", 123)
    payload[0x15] = 87
    payload[0x17:0x1B] = struct.pack("<I", 1234)
    payload[0x1B:0x1F] = struct.pack("<I", 5678)
    payload[0x1F:0x23] = struct.pack("<I", 9012)
    payload[0x27:0x2B] = struct.pack("<I", 345)
    payload[0x2B:0x2F] = struct.pack("<I", 678)
    payload[0x2F:0x31] = struct.pack("<H", 11)
    payload[0x31:0x33] = struct.pack("<H", 12)
    payload[0x33:0x35] = struct.pack("<H", 13)
    payload[0x35:0x37] = struct.pack("<H", 14)
    payload[0x3C] = 5

    parse_into(payload, JupiterPackets.RUNTIME_INFORMATION, data)
    assert [(pv.power, pv.connected) for pv in data.pv_inputs] == [
        (101.0, True),
        (202.0, False),
        (303.0, True),
        (404.0, True),
    ]
    assert data.runtime.ac_output_power == 750.0
    assert data.runtime.ac_output_active is True
    assert data.runtime.battery_charging_active is True
    assert data.runtime.stored_battery_energy == 1230.0
    assert data.runtime.battery_soc == 87.0
    assert data.runtime.operational_status == 5
    assert (
        data.runtime.ems_firmware_version,
        data.runtime.inverter_firmware_version,
        data.runtime.mppt_firmware_version,
        data.runtime.bms_firmware_version,
    ) == (11, 12, 13, 14)
    assert data.energy.daily_pv_generation == pytest.approx(12.34)
    assert data.energy.monthly_pv_generation == pytest.approx(56.78)
    assert data.energy.total_pv_generation == pytest.approx(90.12)
    assert data.energy.daily_discharge_energy == pytest.approx(3.45)
    assert data.energy.monthly_discharge_energy == pytest.approx(6.78)


def test_jupiter_detailed_packet_parses_scaled_and_repeated_battery_data() -> None:
    data = JupiterData()
    payload = bytearray(166)
    payload[0x06:0x08] = struct.pack("<H", 2305)
    payload[0x08:0x0A] = struct.pack("<H", 123)
    payload[0x0C:0x0E] = struct.pack("<H", 5001)
    payload[0x10:0x12] = struct.pack("<h", -321)
    payload[0x12:0x14] = struct.pack("<h", -7)
    payload[0x24:0x26] = struct.pack("<h", 31)
    payload[0x50:0x52] = struct.pack("<H", 512)
    payload[0x52:0x54] = struct.pack("<h", -45)

    first_pv = 0x28
    payload[first_pv : first_pv + 2] = struct.pack("<H", 401)
    payload[first_pv + 2 : first_pv + 4] = struct.pack("<H", 25)
    payload[first_pv + 4 : first_pv + 6] = struct.pack("<H", 999)

    payload[0x58:0x5A] = struct.pack("<H", 584)
    payload[0x5A:0x5C] = struct.pack("<H", 250)
    payload[0x5C:0x5E] = struct.pack("<H", 300)
    payload[0x5E:0x60] = struct.pack("<H", 88)
    payload[0x60:0x62] = struct.pack("<H", 97)
    payload[0x62:0x64] = struct.pack("<H", 2560)
    payload[0x64:0x66] = struct.pack("<H", 42)
    payload[0x66:0x68] = struct.pack("<H", 5123)
    payload[0x68:0x6A] = struct.pack("<h", -123)
    payload[0x6A:0x6C] = struct.pack("<h", 247)
    payload[0x76:0x78] = struct.pack("<H", 2)
    payload[0x78:0x7A] = struct.pack("<H", 2048)

    for index, (high_index, low_index, high_mv, low_mv, status) in enumerate(
        ((7, 3, 3345, 3299, 0x10), (8, 2, 3350, 3301, 0x20))
    ):
        offset = 0x7A + index * 8
        payload[offset] = high_index
        payload[offset + 1] = low_index
        payload[offset + 2 : offset + 4] = struct.pack("<H", high_mv)
        payload[offset + 4 : offset + 6] = struct.pack("<H", low_mv)
        payload[offset + 6 : offset + 8] = struct.pack("<H", status)

    parse_into(payload, JupiterPackets.DETAILED_TELEMETRY, data)
    assert data.inverter.grid_voltage == pytest.approx(230.5)
    assert data.inverter.grid_current == pytest.approx(12.3)
    assert data.inverter.grid_frequency == pytest.approx(50.01)
    assert data.runtime.ac_output_power == -321.0
    assert data.inverter.temperature == -7.0
    assert data.mppt.temperature == 31.0
    assert data.mppt.dc_output_voltage == pytest.approx(51.2)
    assert data.mppt.dc_output_current == pytest.approx(-4.5)
    assert data.pv_inputs[0].voltage == pytest.approx(40.1)
    assert data.pv_inputs[0].current == pytest.approx(2.5)
    assert data.pv_inputs[0].power == pytest.approx(99.9)
    assert data.battery.charge_voltage_limit == pytest.approx(58.4)
    assert data.battery.charge_current_limit == pytest.approx(25.0)
    assert data.battery.discharge_current_limit == pytest.approx(30.0)
    assert data.runtime.battery_soc == 88.0
    assert data.battery.soh == 97.0
    assert data.battery.rated_capacity == 2560.0
    assert data.runtime.bms_firmware_version == 42
    assert data.battery.voltage == pytest.approx(51.23)
    assert data.battery.current == pytest.approx(-12.3)
    assert data.battery.temperature == pytest.approx(24.7)
    assert data.battery.pack_count == 2
    assert data.runtime.stored_battery_energy == 2048.0
    assert data.battery.packs[0].highest_cell_index == 7
    assert data.battery.packs[0].lowest_cell_index == 3
    assert data.battery.packs[0].highest_cell_voltage == pytest.approx(3.345)
    assert data.battery.packs[0].lowest_cell_voltage == pytest.approx(3.299)
    assert data.battery.packs[0].status == 0x10
    assert data.battery.packs[1].status == 0x20


def test_jupiter_event_history_parses_all_fixed_records() -> None:
    data = JupiterData()
    payload = bytearray(160)
    for index in range(20):
        offset = index * 8
        payload[offset : offset + 2] = struct.pack("<H", 2020 + index)
        payload[offset + 2 : offset + 8] = bytes(
            (1 + index % 12, 1 + index % 28, index % 24, index % 60, index, 0x80 + index)
        )

    parse_into(payload, JupiterPackets.EVENT_HISTORY, data)
    first = data.events[0]
    last = data.events[-1]
    assert (first.year, first.month, first.day, first.event_value, first.event_state) == (
        2020,
        1,
        1,
        0,
        0x80,
    )
    assert (last.year, last.month, last.day, last.event_value, last.event_state) == (
        2039,
        8,
        20,
        19,
        0x93,
    )


def test_jupiter_entity_plan_child_devices_presence_and_expansion_detection() -> None:
    data = JupiterData()
    data.battery.pack_count = 2
    plan = JUPITER_PROFILE.build_entity_plan(data)

    assert plan.repeated_counts["pv_inputs"] == 4
    assert plan.repeated_counts["events"] == 20
    assert plan.repeated_counts["battery.packs"] == 2
    assert [device.key for device in plan.devices] == [
        "main",
        "battery_pack_0",
        "battery_pack_1",
    ]
    assert plan.devices[1].name == "Base Battery"
    assert plan.devices[2].name == "Expansion Battery 1"
    assert plan.devices[2].identifier("AA:BB") == "AA:BB:battery_pack:1"

    second_pack = next(
        entity
        for entity in plan.entities
        if entity.unique_key == "battery_pack_1_highest_cell_voltage"
    )
    assert second_pack.is_present(data) is True
    data.battery.pack_count = 1
    assert second_pack.is_present(data) is False

    data.battery.pack_count = 4
    changes = JUPITER_PROFILE.detect_expansion_increases(data, plan)
    assert len(changes) == 1
    change = changes[0]
    assert change.path == ("battery", "packs")
    assert change.configured_count == 2
    assert change.discovered_count == 4
    assert change.maximum_count == 4
    assert change.issue_id == "jupiter_c_plus_battery_packs_expansion_count_increased"


def test_jupiter_derived_battery_entities_cover_missing_and_threshold_states() -> None:
    data = JupiterData()
    assert _battery_power(data) is None
    data.battery.voltage = 52.0
    assert _battery_power(data) is None
    data.battery.current = -2.0
    assert _battery_power(data) == -104.0

    plan = JUPITER_PROFILE.build_entity_plan(data)
    power = next(entity for entity in plan.entities if entity.description.key == "battery_power")
    charging = next(
        entity for entity in plan.entities if entity.description.key == "battery_charging"
    )
    assert power.value_from(data) == -104.0
    assert charging.value_from(data) is False
    assert power.stale_paths == (("battery", "voltage"), ("battery", "current"))

    data.battery.current = 5 / 52
    assert charging.value_from(data) is False
    data.battery.current = 6 / 52
    assert charging.value_from(data) is True

    data.battery.voltage = None
    assert charging.value_from(data) is None


def test_entity_spec_factories_return_expected_platforms() -> None:
    sensor = sensor_entity(key="sensor", name="Sensor")
    binary = binary_sensor_entity(key="binary", name="Binary")
    indexed = indexed_sensor_entities(
        1,
        lambda index: SensorEntityDescription(key=f"indexed_{index}"),
    )
    derived_s = derived_sensor(
        description=SensorEntityDescription(key="derived_sensor"),
        value_fn=lambda data: 1,
    )
    derived_b = derived_binary_sensor(
        description=BinarySensorEntityDescription(key="derived_binary"),
        value_fn=lambda data: True,
    )
    assert sensor.platform is EntityPlatform.SENSOR
    assert binary.platform is EntityPlatform.BINARY_SENSOR
    assert indexed.platform is EntityPlatform.SENSOR
    assert derived_s.platform is EntityPlatform.SENSOR
    assert derived_b.platform is EntityPlatform.BINARY_SENSOR
