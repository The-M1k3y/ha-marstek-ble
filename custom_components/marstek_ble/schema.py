"""Declarative binary packet parsing primitives.

This module is intentionally independent from the existing protocol implementation.
It provides immutable packet and field descriptions plus a generic parser that
updates only the fields represented by the selected packet schema.
"""

from __future__ import annotations

import struct
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import MISSING, Field, dataclass, field, fields, is_dataclass
from types import MappingProxyType
from typing import Any, TypeVar

Converter = Callable[[Any], Any]
PathElement = str | int
DataPath = tuple[PathElement, ...]

_FIELD_SOURCES_METADATA_KEY = "marstek_ble_field_sources"
_FIELD_ENTITIES_METADATA_KEY = "marstek_ble_field_entities"
_INDEXED_ENTITIES_METADATA_KEY = "marstek_ble_indexed_entities"
_SECTION_SOURCES_METADATA_KEY = "marstek_ble_section_sources"
_REPEATED_SECTION_METADATA_KEY = "marstek_ble_repeated_section"


def identity(value: Any) -> Any:
    """Return *value* unchanged."""

    return value


@dataclass(frozen=True, slots=True)
class PacketSchema:
    """Describe one packet payload that may provide dataclass fields."""

    name: str
    command: int
    minimum_length: int = 0
    maximum_length: int | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Packet schema name cannot be empty")
        if not 0 <= self.command <= 0xFF:
            raise ValueError("Packet command must fit in one byte")
        if self.minimum_length < 0:
            raise ValueError("Packet minimum length cannot be negative")
        if (
            self.maximum_length is not None
            and self.maximum_length < self.minimum_length
        ):
            raise ValueError(
                "Packet maximum length cannot be smaller than its minimum length"
            )

    def validate_payload(self, payload: bytes | bytearray | memoryview) -> None:
        """Validate the payload length against this packet schema."""

        payload_length = len(payload)
        if payload_length < self.minimum_length:
            raise ValueError(
                f"{self.name} payload is too short: "
                f"expected at least {self.minimum_length} bytes, "
                f"received {payload_length}"
            )
        if (
            self.maximum_length is not None
            and payload_length > self.maximum_length
        ):
            raise ValueError(
                f"{self.name} payload is too long: "
                f"expected at most {self.maximum_length} bytes, "
                f"received {payload_length}"
            )


@dataclass(frozen=True, slots=True)
class FieldSource:
    """Describe how one packet represents one result field."""

    offset: int
    format: str
    converter: Converter = field(default=identity, repr=False, compare=False)
    minimum_length: int | None = None
    maximum_length: int | None = None
    _struct: struct.Struct = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("Field offset cannot be negative")
        if not self.format or self.format[0] not in "<>=!":
            raise ValueError(
                "Field format must declare byte order explicitly with <, >, =, or !"
            )

        try:
            parser = struct.Struct(self.format)
        except struct.error as error:
            raise ValueError(f"Invalid struct format {self.format!r}") from error

        object.__setattr__(self, "_struct", parser)

        if self.minimum_length is not None and self.minimum_length < 0:
            raise ValueError("Field minimum length cannot be negative")
        if self.maximum_length is not None:
            if self.maximum_length < self.end_offset:
                raise ValueError(
                    "Field maximum length cannot end before the field itself"
                )
            if (
                self.minimum_length is not None
                and self.maximum_length < self.minimum_length
            ):
                raise ValueError(
                    "Field maximum length cannot be smaller than its minimum length"
                )

    @property
    def size(self) -> int:
        """Return the encoded field size in bytes."""

        return self._struct.size

    @property
    def end_offset(self) -> int:
        """Return the first byte offset after this field."""

        return self.offset + self.size

    def applies_to(
        self,
        payload_length: int,
        *,
        base_offset: int = 0,
    ) -> bool:
        """Return whether this source applies to a payload of the given length."""

        required_length = max(
            base_offset + self.end_offset,
            self.minimum_length or 0,
        )
        if payload_length < required_length:
            return False
        return self.maximum_length is None or payload_length <= self.maximum_length

    def parse_from(
        self,
        payload: bytes | bytearray | memoryview,
        *,
        base_offset: int = 0,
    ) -> tuple[Any, Any]:
        """Return ``(raw_value, converted_value)`` from *payload*."""

        absolute_offset = base_offset + self.offset
        if absolute_offset + self.size > len(payload):
            raise ValueError(
                f"Field at offset {absolute_offset} with size {self.size} "
                f"exceeds payload length {len(payload)}"
            )

        unpacked = self._struct.unpack_from(payload, absolute_offset)
        raw_value: Any = unpacked[0] if len(unpacked) == 1 else unpacked
        return raw_value, self.converter(raw_value)


@dataclass(frozen=True, slots=True)
class SectionSource:
    """Locate one nested dataclass section within a packet payload."""

    offset: int = 0

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("Section offset cannot be negative")


@dataclass(frozen=True, slots=True)
class RepeatedSectionSource:
    """Locate a fixed-size sequence of nested records in one packet."""

    offset: int
    stride: int

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("Repeated section offset cannot be negative")
        if self.stride <= 0:
            raise ValueError("Repeated section stride must be positive")


@dataclass(frozen=True, slots=True)
class RepeatedSectionSpec:
    """Describe a fixed-limit list of nested dataclass records."""

    item_type: Callable[[], Any] = field(repr=False, compare=False)
    count: int
    sources: Mapping[PacketSchema, RepeatedSectionSource] = field(
        repr=False,
        compare=False,
    )
    active_count_attribute: str | None = None
    child_device: Any = field(default=None, repr=False, compare=False)
    item_name_factory: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("Repeated section count must be positive")
        if not self.sources:
            raise ValueError("Repeated section requires at least one packet source")
        object.__setattr__(
            self,
            "sources",
            MappingProxyType(dict(self.sources)),
        )


@dataclass(frozen=True, slots=True)
class ParsedField:
    """One pending field update produced by :func:`iter_parsed_fields`."""

    path: DataPath
    value: Any
    raw_value: Any = field(repr=False)
    _target: Any = field(repr=False, compare=False)
    _attribute: str = field(repr=False, compare=False)

    @property
    def path_string(self) -> str:
        """Return the dotted representation used for update metadata."""

        return ".".join(str(part) for part in self.path)

    def apply(self) -> None:
        """Apply this update to its target dataclass instance."""

        setattr(self._target, self._attribute, self.value)


def _field_metadata(
    *,
    sources: Mapping[PacketSchema, FieldSource] | None = None,
    entities: Sequence[Any] = (),
    indexed_entities: Sequence[Any] = (),
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if sources:
        metadata[_FIELD_SOURCES_METADATA_KEY] = MappingProxyType(dict(sources))
    if entities:
        metadata[_FIELD_ENTITIES_METADATA_KEY] = tuple(entities)
    if indexed_entities:
        metadata[_INDEXED_ENTITIES_METADATA_KEY] = tuple(indexed_entities)
    return metadata


def source_field(
    *,
    sources: Mapping[PacketSchema, FieldSource],
    entities: Sequence[Any] = (),
    indexed_entities: Sequence[Any] = (),
    default: Any = None,
    default_factory: Callable[[], Any] | Any = MISSING,
    repr: bool = True,
) -> Any:
    """Create a dataclass field with packet sources and optional entity metadata."""

    if not sources:
        raise ValueError("A source field requires at least one packet source")

    metadata = _field_metadata(
        sources=sources,
        entities=entities,
        indexed_entities=indexed_entities,
    )
    if default_factory is not MISSING:
        return field(
            default_factory=default_factory,
            metadata=metadata,
            repr=repr,
        )
    return field(default=default, metadata=metadata, repr=repr)


def value_field(
    *,
    entities: Sequence[Any],
    indexed_entities: Sequence[Any] = (),
    default: Any = None,
    default_factory: Callable[[], Any] | Any = MISSING,
    repr: bool = True,
) -> Any:
    """Create an entity-backed value with no fixed binary representation yet."""

    if not entities and not indexed_entities:
        raise ValueError("A value field requires entity metadata")

    metadata = _field_metadata(
        entities=entities,
        indexed_entities=indexed_entities,
    )
    if default_factory is not MISSING:
        return field(
            default_factory=default_factory,
            metadata=metadata,
            repr=repr,
        )
    return field(default=default, metadata=metadata, repr=repr)


def section_field(
    section_type: Callable[[], Any],
    *,
    sources: Mapping[PacketSchema, SectionSource] | None = None,
    repr: bool = True,
) -> Any:
    """Create a nested dataclass field, optionally with packet-specific offsets."""

    metadata: dict[str, Any] = {}
    if sources is not None:
        if not sources:
            raise ValueError("Section sources cannot be empty")
        metadata[_SECTION_SOURCES_METADATA_KEY] = MappingProxyType(dict(sources))

    return field(default_factory=section_type, metadata=metadata, repr=repr)


def repeated_section_field(
    section_type: Callable[[], Any],
    *,
    count: int,
    sources: Mapping[PacketSchema, RepeatedSectionSource],
    active_count_attribute: str | None = None,
    child_device: Any = None,
    item_name_factory: Any = None,
    repr: bool = True,
) -> Any:
    """Create a fixed-limit list of nested dataclass records."""

    spec = RepeatedSectionSpec(
        item_type=section_type,
        count=count,
        sources=sources,
        active_count_attribute=active_count_attribute,
        child_device=child_device,
        item_name_factory=item_name_factory,
    )
    return field(
        default_factory=lambda: [section_type() for _ in range(count)],
        metadata={_REPEATED_SECTION_METADATA_KEY: spec},
        repr=repr,
    )


def get_field_sources(
    result_field: Field[Any],
) -> Mapping[PacketSchema, FieldSource] | None:
    """Return packet sources attached to a dataclass field."""

    return result_field.metadata.get(_FIELD_SOURCES_METADATA_KEY)


def get_field_entities(result_field: Field[Any]) -> tuple[Any, ...]:
    """Return direct entity descriptions attached to a dataclass field."""

    return result_field.metadata.get(_FIELD_ENTITIES_METADATA_KEY, ())


def get_indexed_entities(result_field: Field[Any]) -> tuple[Any, ...]:
    """Return indexed entity descriptions attached to a list field."""

    return result_field.metadata.get(_INDEXED_ENTITIES_METADATA_KEY, ())


def get_section_sources(
    result_field: Field[Any],
) -> Mapping[PacketSchema, SectionSource] | None:
    """Return nested-section packet sources attached to a dataclass field."""

    return result_field.metadata.get(_SECTION_SOURCES_METADATA_KEY)


def get_repeated_section(result_field: Field[Any]) -> RepeatedSectionSpec | None:
    """Return repeated-section metadata attached to a dataclass field."""

    return result_field.metadata.get(_REPEATED_SECTION_METADATA_KEY)


def iter_parsed_fields(
    payload: bytes | bytearray | memoryview,
    packet: PacketSchema,
    result: Any,
) -> Iterator[ParsedField]:
    """Yield every field update represented by *packet*.

    Iteration does not mutate *result*. This allows :func:`parse_into` to decode
    the complete packet before applying any updates.
    """

    if not is_dataclass(result) or isinstance(result, type):
        raise TypeError("Result must be a dataclass instance")

    packet.validate_payload(payload)
    yield from _iter_parsed_fields(
        payload,
        packet,
        result,
        base_offset=0,
        path=(),
    )


def _iter_parsed_fields(
    payload: bytes | bytearray | memoryview,
    packet: PacketSchema,
    result: Any,
    *,
    base_offset: int,
    path: DataPath,
) -> Iterator[ParsedField]:
    for result_field in fields(result):
        field_path = (*path, result_field.name)
        field_sources = get_field_sources(result_field)

        if field_sources is not None:
            source = field_sources.get(packet)
            if source is None or not source.applies_to(
                len(payload),
                base_offset=base_offset,
            ):
                continue

            raw_value, value = source.parse_from(payload, base_offset=base_offset)
            yield ParsedField(
                path=field_path,
                value=value,
                raw_value=raw_value,
                _target=result,
                _attribute=result_field.name,
            )
            continue

        repeated_spec = get_repeated_section(result_field)
        if repeated_spec is not None:
            repeated_source = repeated_spec.sources.get(packet)
            if repeated_source is None:
                continue

            current_value = getattr(result, result_field.name)
            if not isinstance(current_value, list):
                raise TypeError(
                    f"Repeated section {'.'.join(str(part) for part in field_path)} "
                    "must contain a list"
                )
            if len(current_value) != repeated_spec.count:
                raise ValueError(
                    f"Repeated section {'.'.join(str(part) for part in field_path)} "
                    f"contains {len(current_value)} items, expected "
                    f"{repeated_spec.count}"
                )

            for index, item in enumerate(current_value):
                if not is_dataclass(item) or isinstance(item, type):
                    raise TypeError("Repeated section items must be dataclass instances")
                yield from _iter_parsed_fields(
                    payload,
                    packet,
                    item,
                    base_offset=(
                        base_offset
                        + repeated_source.offset
                        + index * repeated_source.stride
                    ),
                    path=(*field_path, index),
                )
            continue

        current_value = getattr(result, result_field.name)
        if not is_dataclass(current_value) or isinstance(current_value, type):
            continue

        section_sources = get_section_sources(result_field)
        nested_base_offset = base_offset
        if section_sources is not None:
            section_source = section_sources.get(packet)
            if section_source is None:
                continue
            nested_base_offset += section_source.offset

        yield from _iter_parsed_fields(
            payload,
            packet,
            current_value,
            base_offset=nested_base_offset,
            path=field_path,
        )


T = TypeVar("T")


def parse_into(
    payload: bytes | bytearray | memoryview,
    packet: PacketSchema,
    result: T,
) -> T:
    """Parse *payload* into *result* and return the same result object.

    Only fields declaring *packet* as a source are updated. Values supplied by
    other packets remain untouched. All fields are decoded before any mutation,
    so a decoding error cannot leave the result partially updated.
    """

    updates = tuple(iter_parsed_fields(payload, packet, result))
    for update in updates:
        update.apply()
    return result


def nonzero(value: Any) -> bool:
    """Convert a numeric value to a boolean using nonzero semantics."""

    return value != 0


def bit(bit_number: int) -> Callable[[int], bool]:
    """Return a converter extracting one boolean bit."""

    if bit_number < 0:
        raise ValueError("Bit number cannot be negative")
    mask = 1 << bit_number
    return lambda value: bool(value & mask)


def bits(first_bit: int, bit_count: int) -> Callable[[int], int]:
    """Return a converter extracting an unsigned bit range."""

    if first_bit < 0:
        raise ValueError("First bit cannot be negative")
    if bit_count <= 0:
        raise ValueError("Bit count must be positive")
    mask = (1 << bit_count) - 1
    return lambda value: (value >> first_bit) & mask


def multiply_by(multiplier: float) -> Callable[[int | float], float]:
    """Return a converter multiplying a numeric value."""

    return lambda value: value * multiplier


def divide_by(divisor: float) -> Callable[[int | float], float]:
    """Return a converter dividing a numeric value by *divisor*."""

    if divisor == 0:
        raise ValueError("Divisor cannot be zero")
    return lambda value: value / divisor


def divide_each_by(divisor: float) -> Callable[[Sequence[int | float]], list[float]]:
    """Return a converter dividing every value in a sequence."""

    if divisor == 0:
        raise ValueError("Divisor cannot be zero")
    return lambda values: [value / divisor for value in values]
