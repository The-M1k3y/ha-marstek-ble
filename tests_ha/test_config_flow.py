"""Isolated integration tests against the genuine Home Assistant framework."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.marstek_ble.const import (
    CONF_MEDIUM_POLL_INTERVAL,
    CONF_POLL_INTERVAL,
    CONF_PRODUCT_ID,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_real_flow_manager_aborts_when_no_devices_are_discovered(hass) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


@pytest.mark.asyncio
async def test_real_flow_manager_discovers_and_creates_an_entry(hass, monkeypatch) -> None:
    discovery = SimpleNamespace(
        address="AA:BB:CC:DD:EE:01",
        name="MST_ACCP_SYNTHETIC",
    )
    monkeypatch.setattr(
        "custom_components.marstek_ble.config_flow.async_discovered_service_info",
        lambda _hass: [discovery],
    )

    form = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"],
        {CONF_ADDRESS: discovery.address},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == discovery.name
    assert result["data"] == {
        CONF_ADDRESS: discovery.address,
        CONF_NAME: discovery.name,
        CONF_PRODUCT_ID: "venus",
    }


@pytest.mark.asyncio
async def test_real_options_flow_validates_and_persists_intervals(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:01",
            CONF_NAME: "MST_ACCP_SYNTHETIC",
        },
        unique_id="AA:BB:CC:DD:EE:01",
    )
    entry.add_to_hass(hass)

    form = await hass.config_entries.options.async_init(entry.entry_id)
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {
            CONF_POLL_INTERVAL: 5,
            CONF_MEDIUM_POLL_INTERVAL: 60,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        CONF_POLL_INTERVAL: 5,
        CONF_MEDIUM_POLL_INTERVAL: 60,
    }


@pytest.mark.asyncio
async def test_real_config_entry_lifecycle_retries_without_ble_device(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:01",
            CONF_NAME: "MST_ACCP_SYNTHETIC",
        },
        unique_id="AA:BB:CC:DD:EE:01",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id) is False
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
