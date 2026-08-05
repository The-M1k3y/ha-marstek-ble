"""Declarative binary packet parsing primitives.

This module is intentionally independent from the existing protocol implementation.
It provides immutable packet and field descriptions plus a generic parser that
updates only the fields represented by the selected packet schema.
"""

from __future__ import annotations

import struct
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from types import MappingProxyType
from typing import Any, TypeVar

Converter = Callable[[Any], Any]

_FIELD_SOURCES_METADATA_KEY = "marstek_ble_field_sources"
_SECTION_SOURCES_METADATA_KEY = "marstek_ble_section_sources"


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

    def applies_to(self, payload_length: int) -> bool:
        """Return whether this source applies to a payload of the given length."""

        required_length = max(self.end_offset, self.minimum_length or 0)
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
    """Locate a nested dataclass section within a packet payload."""

    offset: int = 0

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("Section offset cannot be negative")


@dataclass(frozen=True, slots=True)
class ParsedField:
    """One pending field update produced by :func:`iter_parsed_fields`."""

    path: str
    value: Any
    raw_value: Any = field(repr=False)
    _target: Any = field(repr=False, compare=False)
    _attribute: str = field(repr=False, compare=False)

    def apply(self) -> None:
        """Apply this update to its target dataclass instance."""

        setattr(self._target, self._attribute, self.value)


def source_field(
    *,
    sources: Mapping[PacketSchema, FieldSource],
    default: Any = None,
    default_factory: Callable[[], Any] | None = None,
    repr: bool = True,
) -> Any:
    """Create a dataclass field whose packet representations are declared inline."""

    if not sources:
        raise ValueError("A source field requires at least one packet source")

    metadata = {
        _FIELD_SOURCES_METADATA_KEY: MappingProxyType(dict(sources)),
    }

    if default_factory is not None:
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
    path: tuple[str, ...],
) -> Iterator[ParsedField]:
    for result_field in fields(result):
        field_path = (*path, result_field.name)
        field_sources: Mapping[PacketSchema, FieldSource] | None = (
            result_field.metadata.get(_FIELD_SOURCES_METADATA_KEY)
        )

        if field_sources is not None:
            source = field_sources.get(packet)
            if source is None or not source.applies_to(len(payload) - base_offset):
                continue

            raw_value, value = source.parse_from(payload, base_offset=base_offset)
            yield ParsedField(
                path=".".join(field_path),
                value=value,
                raw_value=raw_value,
                _target=result,
                _attribute=result_field.name,
            )
            continue

        current_value = getattr(result, result_field.name)
        if not is_dataclass(current_value) or isinstance(current_value, type):
            continue

        section_sources: Mapping[PacketSchema, SectionSource] | None = (
            result_field.metadata.get(_SECTION_SOURCES_METADATA_KEY)
        )
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
