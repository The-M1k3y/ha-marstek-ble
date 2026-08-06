"""Unit tests for discovery, user setup and options flows."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from bleak.backends.device import BLEDevice
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.marstek_ble.config_flow import (
    MarstekBLEConfigFlow,
    MarstekBLEOptionsFlow,
)
from custom_components.marstek_ble.const import (
    CONF_MEDIUM_POLL_INTERVAL,
    CONF_POLL_INTERVAL,
)


def discovery(address: str, name: str | None) -> BluetoothServiceInfoBleak:
    return BluetoothServiceInfoBleak(address, name, BLEDevice(address, name))


def flow() -> MarstekBLEConfigFlow:
    result = MarstekBLEConfigFlow()
    result.context = {}
    result._current_entries = []
    result._current_ids = set()
    result.hass = HomeAssistant()
    return result


@pytest.mark.asyncio
async def test_bluetooth_discovery_shows_confirmation_and_creates_entry() -> None:
    config_flow = flow()
    info = discovery("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")
    result = await config_flow.async_step_bluetooth(info)
    assert result["type"] == "form"
    assert result["step_id"] == "bluetooth_confirm"
    assert result["description_placeholders"] == {"name": "MST_ACCP_TEST"}
    assert config_flow.context["title_placeholders"] == {"name": "MST_ACCP_TEST"}
    assert config_flow._confirm_only is True
    result = await config_flow.async_step_bluetooth_confirm({})
    assert result == {
        "type": "create_entry",
        "title": "MST_ACCP_TEST",
        "data": {
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "MST_ACCP_TEST",
        },
    }


@pytest.mark.asyncio
async def test_bluetooth_discovery_uses_address_when_name_missing() -> None:
    config_flow = flow()
    info = discovery("AA:BB:CC:DD:EE:FF", None)
    await config_flow.async_step_bluetooth(info)
    result = await config_flow.async_step_bluetooth_confirm({})
    assert result["title"] == info.address
    assert result["data"][CONF_NAME] == info.address


@pytest.mark.asyncio
async def test_bluetooth_discovery_aborts_duplicate_name() -> None:
    config_flow = flow()
    config_flow._current_entries = [
        SimpleNamespace(data={CONF_NAME: "MST_ACCP_TEST", CONF_ADDRESS: "old"})
    ]
    result = await config_flow.async_step_bluetooth(
        discovery("AA:BB:CC:DD:EE:FF", "MST_ACCP_TEST")
    )
    assert result == {"type": "abort", "reason": "already_configured"}


@pytest.mark.asyncio
async def test_user_step_filters_configured_non_marstek_and_unnamed_devices() -> None:
    config_flow = flow()
    config_flow._current_ids = {"AA:00"}
    config_flow._current_entries = [
        SimpleNamespace(data={CONF_NAME: "MST_ACCP_CONFIGURED"})
    ]
    config_flow.hass._discovered_service_info = [
        discovery("AA:00", "MST_ACCP_BY_ADDRESS"),
        discovery("AA:01", "MST_ACCP_CONFIGURED"),
        discovery("AA:02", "OTHER_DEVICE"),
        discovery("AA:03", None),
        discovery("AA:04", "MST_ACCP_VALID"),
        discovery("AA:05", "MST_VNSE3_VALID"),
    ]
    result = await config_flow.async_step_user()
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert set(config_flow._discovered_devices) == {"AA:04", "AA:05"}
    result = await config_flow.async_step_user({CONF_ADDRESS: "AA:05"})
    assert result["type"] == "create_entry"
    assert result["title"] == "MST_VNSE3_VALID"
    assert result["data"] == {
        CONF_ADDRESS: "AA:05",
        CONF_NAME: "MST_VNSE3_VALID",
    }
    assert config_flow._raise_on_progress is False


@pytest.mark.asyncio
async def test_user_step_aborts_when_no_devices_are_available() -> None:
    config_flow = flow()
    config_flow.hass._discovered_service_info = [discovery("AA:01", "OTHER")]
    assert await config_flow.async_step_user() == {
        "type": "abort",
        "reason": "no_devices_found",
    }


def test_options_flow_factory() -> None:
    entry = SimpleNamespace(options={})
    options = MarstekBLEConfigFlow.async_get_options_flow(entry)
    assert isinstance(options, MarstekBLEOptionsFlow)


@pytest.mark.asyncio
async def test_options_flow_uses_defaults_and_saves_input() -> None:
    entry = SimpleNamespace(
        options={CONF_POLL_INTERVAL: 4, CONF_MEDIUM_POLL_INTERVAL: 90}
    )
    options = MarstekBLEOptionsFlow(entry)
    result = await options.async_step_init()
    assert result["type"] == "form"
    schema = result["data_schema"].schema
    defaults = {key.schema: key.default for key in schema}
    assert defaults == {
        CONF_POLL_INTERVAL: 4,
        CONF_MEDIUM_POLL_INTERVAL: 90,
    }
    submitted = {CONF_POLL_INTERVAL: 7, CONF_MEDIUM_POLL_INTERVAL: 120}
    assert await options.async_step_init(submitted) == {
        "type": "create_entry",
        "title": "",
        "data": submitted,
    }


@pytest.mark.asyncio
async def test_user_step_handles_unknown_selected_address() -> None:
    config_flow = flow()
    config_flow._discovered_devices = {
        "AA:01": discovery("AA:01", "MST_ACCP_VALID")
    }
    try:
        result = await config_flow.async_step_user({CONF_ADDRESS: "AA:FF"})
    except KeyError as exc:
        pytest.fail(f"unknown address escaped config flow validation: {exc}")
    assert result["type"] in {"form", "abort"}
