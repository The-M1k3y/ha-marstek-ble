"""Product-aware coordinator for Marstek BLE devices."""

from __future__ import annotations

import logging

from bleak.backends.device import BLEDevice
from homeassistant.core import HomeAssistant

from .coordinator import MarstekDataUpdateCoordinator, VERBOSE_LOGGER
from .product_runtime import PollCommand, ProductProtocol, ProductRuntime

_LOGGER = logging.getLogger(__name__)


class ProductDataUpdateCoordinator(MarstekDataUpdateCoordinator):
    """Coordinator using a product-specific data model and polling profile."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        address: str,
        device: BLEDevice,
        device_name: str,
        product: ProductRuntime,
        poll_interval: int,
        medium_poll_interval: int,
    ) -> None:
        super().__init__(
            hass=hass,
            logger=logger,
            address=address,
            device=device,
            device_name=device_name,
            poll_interval=poll_interval,
            medium_poll_interval=medium_poll_interval,
        )
        self.product = product
        self._protocol = ProductProtocol(product)
        self.data = product.create_data()

    async def _poll_commands(self, commands: tuple[PollCommand, ...]) -> None:
        """Send one product-defined polling schedule in order."""

        for command in commands:
            await self._safe_send_and_sleep(
                command.command,
                command.payload,
                delay=command.delay,
            )

    async def _poll_fast(self) -> None:
        """Poll product-defined fast-update data."""

        VERBOSE_LOGGER.debug(
            "[%s/%s] Polling %s fast data",
            self.device_name,
            self.address,
            self.product.product_id,
        )
        await self._poll_commands(self.product.fast_poll)

    async def _poll_medium(self) -> None:
        """Poll product-defined medium-update data."""

        VERBOSE_LOGGER.debug(
            "[%s/%s] Polling %s medium data",
            self.device_name,
            self.address,
            self.product.product_id,
        )
        await self._poll_commands(self.product.medium_poll)

    def _handle_notification(self, sender: int, data: bytearray) -> None:
        """Parse a notification with the selected product runtime."""

        raw_data = bytes(data)
        command = raw_data[3] if len(raw_data) > 3 else None
        command_label = (
            f"0x{command:02X}" if command is not None else "unknown"
        )
        VERBOSE_LOGGER.debug(
            "[%s/%s] Received %s notification cmd=%s from sender %s",
            self.device_name,
            self.address,
            self.product.product_id,
            command_label,
            sender,
        )

        try:
            result = self._protocol.parse_notification(raw_data, self.data)
        except Exception as error:  # noqa: BLE001
            _LOGGER.exception(
                "[%s/%s] %s notification parser failed for cmd=%s: %s",
                self.device_name,
                self.address,
                self.product.product_id,
                command_label,
                error,
            )
            result = False

        self.device.record_notification(sender, raw_data, result)
        if result:
            self.async_update_listeners()
