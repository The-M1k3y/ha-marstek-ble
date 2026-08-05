"""Unit tests for diagnostics collection and redaction."""
from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest

from bleak.backends.device import BLEDevice
from homeassistant.core import HomeAssistant

from custom_components.marstek_ble import diagnostics
from custom_components.marstek_ble.const import DOMAIN
from custom_components.marstek_ble.marstek_device import MarstekData


def test_load_manifest_version() -> None:
    assert diagnostics._load_manifest_version() == "0.4.0-rc3"


def test_load_manifest_version_handles_missing_and_invalid_json(monkeypatch) -> None:
    class Missing:
        def joinpath(self, name):
            return self

        def read_text(self, encoding):
            raise FileNotFoundError

    monkeypatch.setattr(diagnostics.resources, "files", lambda package: Missing())
    assert diagnostics._load_manifest_version() is None

    class Invalid:
        def joinpath(self, name):
            return self

        def read_text(self, encoding):
            return "not json"

    monkeypatch.setattr(diagnostics.resources, "files", lambda package: Invalid())
    assert diagnostics._load_manifest_version() is None


def test_dataclass_to_dict_only_converts_dataclasses() -> None:
    data = MarstekData(battery_soc=42)
    converted = diagnostics._dataclass_to_dict(data)
    assert converted["battery_soc"] == 42
    marker = object()
    assert diagnostics._dataclass_to_dict(marker) is marker


def fake_coordinator() -> SimpleNamespace:
    data = MarstekData(
        battery_soc=42,
        wifi_ssid="Private WiFi",
        meter_ip="192.0.2.10",
        network_info="ip:192.0.2.20",
        mac_address="AA:BB:CC:DD:EE:FF",
        device_id="device-secret",
        serial_number="serial-secret",
    )
    device_diagnostics = {
        "connected": True,
        "address": "AA:BB:CC:DD:EE:FF",
        "recent_commands": [],
    }
    return SimpleNamespace(
        device=SimpleNamespace(get_diagnostics=lambda: device_diagnostics),
        device_name="Battery",
        ble_device=BLEDevice("AA:BB:CC:DD:EE:FF"),
        _ready_event=SimpleNamespace(is_set=lambda: True),
        _was_unavailable=False,
        last_poll_successful=True,
        _poll_interval=2,
        _medium_poll_interval=60,
        update_interval=timedelta(seconds=2),
        _fast_poll_count=10,
        _medium_poll_count=2,
        _medium_poll_cycle=30,
        data=data,
    )


def entry(coordinator) -> SimpleNamespace:
    return SimpleNamespace(
        entry_id="entry-1",
        title="Battery",
        source="bluetooth",
        unique_id="AA:BB:CC:DD:EE:FF",
        minor_version=1,
        version=1,
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "Battery"},
        options={"poll_interval": 2},
        runtime_data=coordinator,
    )


def test_coordinator_diagnostics_contains_poll_and_device_state() -> None:
    snapshot = diagnostics._coordinator_diagnostics(fake_coordinator())
    assert snapshot["ready"] is True
    assert snapshot["last_poll_successful"] is True
    assert snapshot["polling"] == {
        "configured_fast_interval_seconds": 2,
        "configured_medium_interval_seconds": 60,
        "active_update_interval_seconds": 2.0,
        "fast_poll_count": 10,
        "medium_poll_count": 2,
        "medium_poll_cycle": 30,
    }
    assert snapshot["coordinator_data"]["battery_soc"] == 42
    assert snapshot["device_connected"] is True


@pytest.mark.asyncio
async def test_diagnostics_uses_runtime_or_hass_fallback_and_redacts_known_fields() -> None:
    hass = HomeAssistant()
    coordinator = fake_coordinator()
    config_entry = entry(coordinator)
    result = await diagnostics.async_get_config_entry_diagnostics(hass, config_entry)
    data = result["coordinator"]["coordinator_data"]
    assert data["wifi_ssid"] == "**REDACTED**"
    assert data["meter_ip"] == "**REDACTED**"
    assert data["network_info"] == "**REDACTED**"
    assert data["mac_address"] == "**REDACTED**"
    assert data["device_id"] == "**REDACTED**"
    assert result["environment"]["integration_version"] == "0.4.0-rc3"
    config_entry.runtime_data = None
    hass.data[DOMAIN] = {config_entry.entry_id: {"coordinator": coordinator}}
    fallback = await diagnostics.async_get_config_entry_diagnostics(hass, config_entry)
    assert fallback["coordinator"]["device_name"] == "Battery"


@pytest.mark.asyncio
async def test_diagnostics_reports_missing_coordinator() -> None:
    hass = HomeAssistant()
    config_entry = entry(None)
    assert await diagnostics.async_get_config_entry_diagnostics(hass, config_entry) == {
        "error": "coordinator_not_available"
    }


@pytest.mark.known_issue
@pytest.mark.asyncio
async def test_diagnostics_redacts_all_device_identifiers() -> None:
    hass = HomeAssistant()
    coordinator = fake_coordinator()
    result = await diagnostics.async_get_config_entry_diagnostics(
        hass, entry(coordinator)
    )
    serialized = repr(result)
    for secret in (
        "serial-secret",
        "AA:BB:CC:DD:EE:FF",
        "device-secret",
        "192.0.2.10",
        "192.0.2.20",
        "Private WiFi",
    ):
        assert secret not in serialized
