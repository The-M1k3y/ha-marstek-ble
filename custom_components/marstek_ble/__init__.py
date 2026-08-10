"""Marstek BLE integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_MEDIUM_POLL_INTERVAL,
    CONF_POLL_INTERVAL,
    CONF_PRODUCT_ID,
    DEFAULT_MEDIUM_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)
from .coordinator import MarstekDataUpdateCoordinator
from .product_coordinator import ProductDataUpdateCoordinator
from .products import VENUS_RUNTIME, runtime_for_id, runtime_for_name

_LOGGER = logging.getLogger(__name__)

READ_ONLY_PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.SELECT,
]


def _platforms_for_product(product_id: str) -> list[Platform]:
    """Return platforms supported by one product runtime."""

    return PLATFORMS if product_id == VENUS_RUNTIME.product_id else READ_ONLY_PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Marstek BLE from a config entry."""

    _LOGGER.debug("Setting up Marstek BLE entry: %s", entry.data)

    address = entry.data.get("address")
    if not address:
        raise ConfigEntryNotReady("Missing Bluetooth address")

    product_id = entry.data.get(CONF_PRODUCT_ID)
    product = runtime_for_id(product_id) if product_id else None
    if product is None and product_id is not None:
        raise ConfigEntryNotReady(f"Unsupported Marstek product: {product_id}")

    if product is None:
        ble_device = None
        try:
            from homeassistant.components.bluetooth import async_ble_device_from_address

            ble_device = async_ble_device_from_address(
                hass, address, connectable=True
            )
        except Exception:  # noqa: BLE001
            ble_device = None

        product = runtime_for_name(
            getattr(ble_device, "name", None) if ble_device is not None else None
        )
        if product is None:
            product = VENUS_RUNTIME

    coordinator = ProductDataUpdateCoordinator(
        hass,
        _LOGGER,
        address,
        product,
        poll_interval=entry.options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        ),
        medium_poll_interval=entry.options.get(
            CONF_MEDIUM_POLL_INTERVAL, DEFAULT_MEDIUM_POLL_INTERVAL
        ),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady from err

    entry.runtime_data = coordinator
    entry.async_on_unload(
        entry.add_update_listener(_async_handle_entry_update)
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

    product_id = None
    if domain_data:
        product_id = domain_data.get("product_id")
    if product_id is None and coordinator is not None:
        product = getattr(coordinator, "product", None)
        product_id = getattr(product, "product_id", None)
    if product_id is None:
        product_id = entry.data.get(
            CONF_PRODUCT_ID, VENUS_RUNTIME.product_id
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
