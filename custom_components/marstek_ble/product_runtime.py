"""Runtime adapters for product-specific Marstek data models."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

from .entity import ProductProfile
from .schema import DataPath, PacketSchema, iter_parsed_fields

_LOGGER = logging.getLogger(__name__)

PayloadParser = Callable[[bytes, Any], tuple[DataPath, ...] | None]


@dataclass(frozen=True, slots=True)
class PollCommand:
    """One command in a product polling schedule."""

    command: int
    payload: bytes = b""
    delay: float = 0.3

    def __post_init__(self) -> None:
        if not 0 <= self.command <= 0xFF:
            raise ValueError("Poll command must fit in one byte")
        if self.delay < 0:
            raise ValueError("Poll command delay cannot be negative")
        object.__setattr__(self, "payload", bytes(self.payload))


class TrackedProductData:
    """Mixin for cumulative product data with per-field update metadata."""

    field_updates: dict[str, dict[str, Any]]

    def _metadata_aliases(self, path: DataPath) -> tuple[str, ...]:
        """Return compatibility metadata keys for a canonical field path."""

        if not path:
            return ()
        return (str(path[-1]),)

    @staticmethod
    def _path_key(path: DataPath) -> str:
        return ".".join(str(part) for part in path)

    def mark_field_update(
        self,
        field: str | DataPath,
        command: int,
        *,
        timestamp: float | None = None,
        payload: bytes | None = None,
    ) -> None:
        """Record when a field path was last updated and by which command."""

        ts = timestamp if timestamp is not None else time.time()
        if isinstance(field, str):
            keys = (field,)
        else:
            canonical = self._path_key(field)
            keys = (canonical, *self._metadata_aliases(field))

        entry = {
            "command": command,
            "timestamp": ts,
            "payload_hex": payload.hex() if payload else None,
        }
        for key in dict.fromkeys(keys):
            self.field_updates[key] = dict(entry)

    def get_field_metadata(
        self, field: str | DataPath
    ) -> dict[str, Any] | None:
        """Return update metadata for a field or canonical data path."""

        key = field if isinstance(field, str) else self._path_key(field)
        entry = self.field_updates.get(key)
        if not entry:
            return None

        timestamp = entry.get("timestamp")
        age = time.time() - timestamp if timestamp is not None else None
        return {
            "command": entry.get("command"),
            "command_hex": (
                f"0x{entry['command']:02X}"
                if entry.get("command") is not None
                else None
            ),
            "timestamp": (
                datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
                if timestamp is not None
                else None
            ),
            "age_seconds": age,
            "payload_hex": entry.get("payload_hex"),
        }


@dataclass(frozen=True, slots=True)
class ProductRuntime:
    """Runtime parsing and polling behavior for one product profile."""

    profile: ProductProfile
    fast_poll: tuple[PollCommand, ...]
    medium_poll: tuple[PollCommand, ...] = ()
    payload_parsers: Mapping[int, PayloadParser] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )
    _packets_by_command: Mapping[int, PacketSchema] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        packets: dict[int, PacketSchema] = {}
        for packet in self.profile.packets:
            if packet.command in packets:
                raise ValueError(
                    f"{self.profile.product_id} defines command "
                    f"0x{packet.command:02X} more than once"
                )
            packets[packet.command] = packet

        parsers = dict(self.payload_parsers)
        for command in parsers:
            if not 0 <= command <= 0xFF:
                raise ValueError("Payload parser command must fit in one byte")

        object.__setattr__(self, "_packets_by_command", MappingProxyType(packets))
        object.__setattr__(self, "payload_parsers", MappingProxyType(parsers))

    @property
    def product_id(self) -> str:
        """Return the stable product identifier."""

        return self.profile.product_id

    def matches_name(self, local_name: str | None) -> bool:
        """Return whether a Bluetooth local name belongs to this product."""

        if not local_name:
            return False
        return any(
            local_name.startswith(prefix)
            for prefix in self.profile.discovery_prefixes
        )

    def create_data(self) -> Any:
        """Create the product-specific cumulative data object."""

        return self.profile.create_data()

    def parse_payload(
        self,
        command: int,
        payload: bytes,
        data: Any,
    ) -> tuple[DataPath, ...] | None:
        """Parse one response payload and return the paths it updated."""

        if not isinstance(data, self.profile.data_type):
            raise TypeError(
                f"{self.product_id} expects {self.profile.data_type.__name__}"
            )

        packet = self._packets_by_command.get(command)
        parser = self.payload_parsers.get(command)
        if packet is None and parser is None:
            return None

        if packet is not None:
            packet.validate_payload(payload)

        if parser is not None:
            return parser(payload, data)

        if packet is None:
            return None

        updates = tuple(iter_parsed_fields(payload, packet, data))
        for update in updates:
            update.apply()
        return tuple(update.path for update in updates)


class ProductProtocol:
    """Frame validation and product-specific payload dispatch."""

    def __init__(self, runtime: ProductRuntime) -> None:
        self.runtime = runtime

    @staticmethod
    def build_command(command: int, payload: bytes = b"") -> bytes:
        """Build a Marstek command frame."""

        frame = bytearray((0x73, 0x00, 0x23, command))
        frame.extend(payload)
        frame[1] = len(frame) + 1

        checksum = 0
        for value in frame:
            checksum ^= value
        frame.append(checksum)
        return bytes(frame)

    def parse_notification(self, frame: bytes, data: Any) -> bool:
        """Validate and parse one notification into product-specific data."""

        if len(frame) < 5:
            _LOGGER.warning("Notification too short (%d bytes)", len(frame))
            return False
        if frame[0] != 0x73 or frame[2] != 0x23:
            _LOGGER.warning(
                "Invalid header: %02X %02X %02X",
                frame[0],
                frame[1],
                frame[2],
            )
            return False
        if frame[1] != len(frame):
            _LOGGER.warning(
                "Invalid notification length: declared %d, actual %d",
                frame[1],
                len(frame),
            )
            return False

        checksum = 0
        for value in frame[:-1]:
            checksum ^= value
        if frame[-1] != checksum:
            _LOGGER.warning(
                "Invalid checksum: expected 0x%02X, got 0x%02X",
                checksum,
                frame[-1],
            )
            return False

        command = frame[3]
        payload = frame[4:-1]
        timestamp = time.time()

        try:
            paths = self.runtime.parse_payload(command, payload, data)
            if paths is None:
                return False

            marker = getattr(data, "mark_field_update", None)
            if marker is not None:
                for path in paths:
                    marker(
                        path,
                        command,
                        timestamp=timestamp,
                        payload=payload,
                    )
            return True
        except Exception as error:  # noqa: BLE001
            _LOGGER.exception(
                "Error parsing %s command 0x%02X: %s",
                self.runtime.product_id,
                command,
                error,
            )
            return False
