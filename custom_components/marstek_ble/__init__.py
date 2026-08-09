"""The Marstek BLE integration."""

from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_MEDIUM_POLL_INTERVAL,
    CONF_POLL_INTERVAL,
    CONF_PRODUCT_ID,
    DEFAULT_MEDIUM_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)
from .product_coordinator import (
    ProductDataUpdateCoordinator as MarstekDataUpdateCoordinator,
)
from .products import VENUS_RUNTIME, runtime_for_id, runtime_for_name

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.SELECT,
]
READ_ONLY_PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


def _platforms_for_product(product_id: str) -> list[Platform]:
    """Return only platforms whose command semantics are valid for a product."""

    return PLATFORMS if product_id == VENUS_RUNTIME.product_id else READ_ONLY_PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Marstek BLE from a config entry."""

    _LOGGER.debug("Setting up Marstek BLE entry: %s", entry.data)

    address: str = entry.data[CONF_ADDRESS]
    device_name: str = entry.data.get(CONF_NAME, entry.title)
    poll_interval: int = entry.options.get(
        CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
    )
    medium_poll_interval: int = entry.options.get(
        CONF_MEDIUM_POLL_INTERVAL, DEFAULT_MEDIUM_POLL_INTERVAL
    )

    for other_entry in hass.config_entries.async_entries(DOMAIN):
        if other_entry.entry_id != entry.entry_id:
            other_name = other_entry.data.get(CONF_NAME, other_entry.title)
            other_address = other_entry.data.get(CONF_ADDRESS)
            if other_name == device_name and other_address != address:
                _LOGGER.warning(
                    "Found duplicate device name '%s': this entry uses address %s, "
                    "but another entry uses address %s. This may cause data to be "
                    "reported incorrectly. Please remove duplicate config entries.",
                    device_name,
                    address,
                    other_address,
                )

    ble_device = bluetooth.async_ble_device_from_address(
        hass, address.upper(), connectable=True
    )
    if not ble_device:
        raise ConfigEntryNotReady(
            f"Could not find Marstek device with address {address}"
        )

    configured_product_id = entry.data.get(CONF_PRODUCT_ID)
    if configured_product_id is not None:
        product = runtime_for_id(configured_product_id)
        if product is None:
            raise ConfigEntryNotReady(
                f"Unsupported Marstek product profile {configured_product_id!r}"
            )
    else:
        # Entries created before product IDs were persisted are Venus entries.
        product = (
            runtime_for_name(device_name)
            or runtime_for_name(getattr(ble_device, "name", None))
            or VENUS_RUNTIME
        )

    _LOGGER.debug(
        "Selected product runtime %s for %s",
        product.product_id,
        device_name,
    )

    coordinator = entry.runtime_data = MarstekDataUpdateCoordinator(
        hass=hass,
        logger=_LOGGER,
        address=address,
        device=ble_device,
        device_name=device_name,
        product=product,
        poll_interval=poll_interval,
        medium_poll_interval=medium_poll_interval,
    )

    entry.async_on_unload(coordinator.async_start())
    entry.async_on_unload(entry.add_update_listener(_async_handle_entry_update))

    if not await coordinator.async_wait_ready():
        raise ConfigEntryNotReady(
            f"Device {address} not advertising, will retry later"
        )

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_BLUETOOTH, address)},
        identifiers={(DOMAIN, address)},
        name=device_name,
        manufacturer=product.profile.device.manufacturer,
        model=product.profile.device.model,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "product_id": product.product_id,
    }

    await hass.config_entries.async_forward_entry_setups(
        entry, _platforms_for_product(product.product_id)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    _LOGGER.debug("Unloading Marstek BLE entry: %s", entry.data)

    domain_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    coordinator: MarstekDataUpdateCoordinator | None = (
        domain_data.get("coordinator") if domain_data else None
    )
    if coordinator:
        try:
            await coordinator.device.disconnect()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to disconnect Marstek BLE device while unloading %s: %s",
                entry.entry_id,
                err,
            )

    product_id = (
        coordinator.product.product_id
        if coordinator is not None
        else entry.data.get(CONF_PRODUCT_ID, VENUS_RUNTIME.product_id)
    )
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, _platforms_for_product(product_id)
    )

    if unload_ok:
        domain_data = hass.data.get(DOMAIN)
        if domain_data:
            domain_data.pop(entry.entry_id, None)
            if not domain_data:
                hass.data.pop(DOMAIN)

    return unload_ok


async def _async_handle_entry_update(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle updates to the config entry options."""

    coordinator: MarstekDataUpdateCoordinator | None = entry.runtime_data
    if coordinator is None:
        return

    poll_interval = entry.options.get(
        CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
    )
    medium_poll_interval = entry.options.get(
        CONF_MEDIUM_POLL_INTERVAL, DEFAULT_MEDIUM_POLL_INTERVAL
    )
    coordinator.set_poll_intervals(poll_interval, medium_poll_interval)
