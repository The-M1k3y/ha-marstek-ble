"""Synthetic golden-replay tests for the original Venus parser."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.marstek_ble.marstek_device import MarstekData, MarstekProtocol
from standalone_test import marstek_basic_info as standalone


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "venus_replay.json"


def _assert_expected(actual: Any, expected: Any) -> None:
    if isinstance(expected, float):
        assert actual == pytest.approx(expected)
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected, strict=True):
            _assert_expected(actual_item, expected_item)
    else:
        assert actual == expected


def test_synthetic_venus_replay_updates_expected_fields_in_order() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data = MarstekData()

    for packet in fixture["packets"]:
        command = int(packet["command"], 16)
        payload = bytes.fromhex(packet["payload_hex"])
        frame = MarstekProtocol.build_command(command, payload)

        assert standalone.parse_frame(frame) == (command, payload)
        assert MarstekProtocol.parse_notification(frame, data) is True

        for field, expected in packet["expected"].items():
            _assert_expected(getattr(data, field), expected)
            tracked_fields = (
                [f"cell_{index}_voltage" for index in range(1, 17)]
                if field == "cell_voltages"
                else [field]
            )
            for tracked_field in tracked_fields:
                metadata = data.field_updates[tracked_field]
                assert metadata["command"] == command
                assert metadata["payload_hex"] == packet["payload_hex"]

    for field, expected in fixture["final_expected"].items():
        _assert_expected(getattr(data, field), expected)


def test_replay_fixture_contains_only_synthetic_nonidentifying_values() -> None:
    """Guard the committed replay fixture against accidental capture replacement."""
    raw = FIXTURE_PATH.read_text(encoding="utf-8")
    fixture = json.loads(raw)

    assert fixture["provenance"] == "synthetic"
    assert fixture["product"] == "Venus"
    assert "AA:BB:CC:DD:EE:FF" not in raw
    assert "192.168." not in raw
    assert all(packet["name"] for packet in fixture["packets"])
