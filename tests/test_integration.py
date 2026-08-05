"""Unit tests for config-entry setup, update and unload lifecycle."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from bleak.backends.device import BLEDevice
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

import custom_components.marstek_ble as integration_module
from custom_components.marstek_ble.const import (
    CONF_MEDIUM_POLL_INTERVAL,
    CONF_POLL_INTERVAL,
    DOMAIN,
)


class FakeConfigEntries:
    def __init__(self, entries=None, *, unload_ok=True) -> None:
        self.entries = list(entries or [])
        self.forward_calls = []
        self.unload_calls = []
        self.unload_ok = unload_ok

    def async_entries(self, domain):
        return self.entries

    async def async_forward_entry_setups(self, entry, platforms):
        self.forward_calls.append((entry, platforms))

    async def async_unload_platforms(self, entry, platforms):
        self.unload_calls.append((entry, platforms))
        return self.unload_ok


class FakeEntry:
    def __init__(
        self,
        *,
        address="AA:BB:CC:DD:EE:FF",
        name="Battery",
        options=None,
    ):
        self.entry_id = "entry-1"
        self.title = name
        self.data = {CONF_ADDRESS: address, CONF_NAME: name}
        self.options = dict(options or {})
        self.runtime_data = None
        self.unload_callbacks = []
        self.update_listener = None

    def async_on_unload(self, callback):
        self.unload_callbacks.append(callback)

    def add_update_listener(self, callback):
        self.update_listener = callback
        return lambda: None


class FakeCoordinator:
    ready = True
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.device = SimpleNamespace(disconnect=self.disconnect)
        self.start_count = 0
        self.disconnect_count = 0
        self.interval_calls = []
        FakeCoordinator.instances.append(self)

    def async_start(self):
        self.start_count += 1
        return lambda: None

    async def async_wait_ready(self):
        return self.ready

    async def disconnect(self):
        self.disconnect_count += 1

    def set_poll_intervals(self, fast, medium):
        self.interval_calls.append((fast, medium))


@pytest.fixture(autouse=True)
def reset_fake_coordinator():
    FakeCoordinator.instances.clear()
    FakeCoordinator.ready = True


def make_hass(entry=None):
    hass = HomeAssistant()
    hass.config_entries = FakeConfigEntries([entry] if entry else [])
    return hass


@pytest.mark.asyncio
async def test_setup_entry_creates_coordinator_device_and_platforms(monkeypatch) -> None:
    entry = FakeEntry(
        options={CONF_POLL_INTERVAL: 3, CONF_MEDIUM_POLL_INTERVAL: 75}
    )
    hass = make_hass(entry)
    ble = BLEDevice(entry.data[CONF_ADDRESS], "MST_ACCP_TEST")
    hass._ble_devices[entry.data[CONF_ADDRESS].upper()] = ble
    monkeypatch.setattr(
        integration_module, "MarstekDataUpdateCoordinator", FakeCoordinator
    )
    assert await integration_module.async_setup_entry(hass, entry) is True
    coordinator = FakeCoordinator.instances[0]
    assert entry.runtime_data is coordinator
    assert coordinator.kwargs["poll_interval"] == 3
    assert coordinator.kwargs["medium_poll_interval"] == 75
    assert len(entry.unload_callbacks) == 2
    assert entry.update_listener is integration_module._async_handle_entry_update
    assert hass.data[DOMAIN][entry.entry_id]["coordinator"] is coordinator
    assert hass.config_entries.forward_calls[0][1] == integration_module.PLATFORMS
    registry_call = hass._device_registry.calls[0]
    assert registry_call["name"] == "Battery"
    assert registry_call["model"] == "Venus E"


@pytest.mark.asyncio
async def test_setup_entry_raises_when_ble_device_is_missing(monkeypatch) -> None:
    entry = FakeEntry()
    hass = make_hass(entry)
    monkeypatch.setattr(
        integration_module, "MarstekDataUpdateCoordinator", FakeCoordinator
    )
    with pytest.raises(ConfigEntryNotReady, match="Could not find"):
        await integration_module.async_setup_entry(hass, entry)
    assert FakeCoordinator.instances == []


@pytest.mark.asyncio
async def test_setup_entry_raises_when_device_never_advertises(monkeypatch) -> None:
    entry = FakeEntry()
    hass = make_hass(entry)
    hass._ble_devices[entry.data[CONF_ADDRESS].upper()] = BLEDevice(
        entry.data[CONF_ADDRESS]
    )
    FakeCoordinator.ready = False
    monkeypatch.setattr(
        integration_module, "MarstekDataUpdateCoordinator", FakeCoordinator
    )
    with pytest.raises(ConfigEntryNotReady, match="not advertising"):
        await integration_module.async_setup_entry(hass, entry)
    assert DOMAIN not in hass.data


@pytest.mark.asyncio
async def test_entry_update_applies_options_and_handles_missing_runtime() -> None:
    entry = FakeEntry(
        options={CONF_POLL_INTERVAL: 8, CONF_MEDIUM_POLL_INTERVAL: 100}
    )
    coordinator = FakeCoordinator()
    entry.runtime_data = coordinator
    await integration_module._async_handle_entry_update(HomeAssistant(), entry)
    assert coordinator.interval_calls == [(8, 100)]
    entry.runtime_data = None
    await integration_module._async_handle_entry_update(HomeAssistant(), entry)


@pytest.mark.asyncio
async def test_unload_disconnects_and_cleans_domain_data() -> None:
    entry = FakeEntry()
    hass = make_hass(entry)
    coordinator = FakeCoordinator()
    hass.data[DOMAIN] = {entry.entry_id: {"coordinator": coordinator}}
    assert await integration_module.async_unload_entry(hass, entry) is True
    assert coordinator.disconnect_count == 1
    assert DOMAIN not in hass.data
    assert len(hass.config_entries.unload_calls) == 1


@pytest.mark.asyncio
async def test_failed_platform_unload_preserves_domain_data() -> None:
    entry = FakeEntry()
    hass = make_hass(entry)
    hass.config_entries.unload_ok = False
    coordinator = FakeCoordinator()
    hass.data[DOMAIN] = {entry.entry_id: {"coordinator": coordinator}}
    assert await integration_module.async_unload_entry(hass, entry) is False
    assert entry.entry_id in hass.data[DOMAIN]


@pytest.mark.known_issue
@pytest.mark.asyncio
async def test_disconnect_failure_does_not_prevent_platform_unload_and_cleanup() -> None:
    entry = FakeEntry()
    hass = make_hass(entry)

    async def fail_disconnect():
        raise RuntimeError("disconnect failed")

    coordinator = SimpleNamespace(
        device=SimpleNamespace(disconnect=fail_disconnect)
    )
    hass.data[DOMAIN] = {entry.entry_id: {"coordinator": coordinator}}
    try:
        result = await integration_module.async_unload_entry(hass, entry)
    except RuntimeError as exc:
        pytest.fail(f"disconnect failure aborted unload: {exc}")
    assert result is True
    assert len(hass.config_entries.unload_calls) == 1
    assert DOMAIN not in hass.data
