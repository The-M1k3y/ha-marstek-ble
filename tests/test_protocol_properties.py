"""Deterministic property and fuzz tests for the original protocol code."""
from __future__ import annotations

import copy
import random

import pytest

from custom_components.marstek_ble.marstek_device import MarstekData, MarstekProtocol
from standalone_test import marstek_basic_info as standalone


_RANDOM_SEED = 0x4D41525354454B


def _xor_checksum(data: bytes) -> int:
    checksum = 0
    for value in data:
        checksum ^= value
    return checksum


def _random_bytes(rng: random.Random, length: int) -> bytes:
    return bytes(rng.randrange(256) for _ in range(length))


def test_random_command_frames_preserve_envelope_payload_and_checksum() -> None:
    """Exercise the complete one-byte command and length domains deterministically."""
    rng = random.Random(_RANDOM_SEED)

    for command in range(256):
        payload_length = rng.randrange(0, 251)
        payload = _random_bytes(rng, payload_length)
        packet = MarstekProtocol.build_command(command, payload)

        assert packet[0] == 0x73
        assert packet[1] == len(packet)
        assert packet[2] == 0x23
        assert packet[3] == command
        assert packet[4:-1] == payload
        assert packet[-1] == _xor_checksum(packet[:-1])


def test_original_frame_implementations_round_trip_each_other() -> None:
    """Both original tools must agree on valid frames and their payloads."""
    rng = random.Random(_RANDOM_SEED ^ 0x5254)

    for _ in range(512):
        command = rng.randrange(256)
        payload = _random_bytes(rng, rng.randrange(0, 251))

        integration_frame = MarstekProtocol.build_command(command, payload)
        assert standalone.parse_frame(integration_frame) == (command, payload)

        standalone_frame = standalone.create_command_frame(command, payload)
        assert standalone_frame == integration_frame
        assert standalone.parse_frame(standalone_frame) == (command, payload)


def test_single_byte_corruption_is_rejected_without_updating_data() -> None:
    """A changed byte with an unchanged checksum must never be accepted."""
    rng = random.Random(_RANDOM_SEED ^ 0x434F5252555054)

    for _ in range(256):
        command = rng.randrange(256)
        payload = _random_bytes(rng, rng.randrange(1, 80))
        packet = bytearray(MarstekProtocol.build_command(command, payload))
        index = rng.randrange(0, len(packet) - 1)
        packet[index] ^= rng.randrange(1, 256)
        corrupted = bytes(packet)

        data = MarstekData()
        assert MarstekProtocol.parse_notification(corrupted, data) is False
        assert data == MarstekData()
        with pytest.raises(ValueError):
            standalone.parse_frame(corrupted)


def test_arbitrary_byte_strings_never_escape_the_notification_parser() -> None:
    """Fuzz malformed input and require a boolean result and atomic rejection."""
    rng = random.Random(_RANDOM_SEED ^ 0x46555A5A)

    for length in range(256):
        for _ in range(4):
            packet = _random_bytes(rng, length)
            data = MarstekData()
            before = copy.deepcopy(data)

            result = MarstekProtocol.parse_notification(packet, data)

            assert isinstance(result, bool)
            if not result:
                assert data == before


@pytest.mark.parametrize(
    ("command", "minimum_length"),
    [
        (0x03, 37),
        (0x0D, 11),
        (0x13, 45),
        (0x14, 80),
        (0x1A, 17),
        (0x22, 1),
        (0x28, 3),
    ],
)
def test_payload_length_boundaries_are_stable(
    command: int, minimum_length: int
) -> None:
    """Check every byte immediately around fixed parser length boundaries."""
    for length in range(max(0, minimum_length - 2), minimum_length + 3):
        result = MarstekProtocol.parse_notification(
            MarstekProtocol.build_command(command, bytes(length)),
            MarstekData(),
        )
        assert result is (length >= minimum_length)


def test_frame_buffer_reassembles_random_fragmentation_and_batching() -> None:
    """Valid frames must survive arbitrary notification fragmentation."""
    rng = random.Random(_RANDOM_SEED ^ 0x4652414D45)

    for _ in range(128):
        expected = [
            standalone.create_command_frame(
                rng.randrange(256),
                _random_bytes(rng, rng.randrange(0, 80)),
            )
            for _ in range(rng.randrange(1, 12))
        ]
        stream = b"".join(expected)
        split_points = sorted(
            set(rng.randrange(1, len(stream)) for _ in range(rng.randrange(0, 30)))
        )
        chunks = []
        start = 0
        for end in split_points:
            chunks.append(stream[start:end])
            start = end
        chunks.append(stream[start:])

        decoder = standalone.FrameBuffer()
        actual: list[bytes] = []
        for chunk in chunks:
            actual.extend(decoder.feed(chunk))

        assert actual == expected


def test_frame_buffer_discards_noise_that_contains_no_start_marker() -> None:
    """Noise before and between frames must not change valid output order."""
    rng = random.Random(_RANDOM_SEED ^ 0x4E4F495345)
    allowed_noise = [value for value in range(256) if value != standalone.START_BYTE]

    for _ in range(128):
        first = standalone.create_command_frame(rng.randrange(256), b"first")
        second = standalone.create_command_frame(rng.randrange(256), b"second")
        prefix = bytes(rng.choice(allowed_noise) for _ in range(rng.randrange(0, 64)))
        middle = bytes(rng.choice(allowed_noise) for _ in range(rng.randrange(0, 64)))
        suffix = bytes(rng.choice(allowed_noise) for _ in range(rng.randrange(0, 64)))

        decoder = standalone.FrameBuffer()
        assert decoder.feed(prefix + first + middle + second + suffix) == [first, second]
