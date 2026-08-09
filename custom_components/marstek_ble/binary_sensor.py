"""Binary sensor platform for Marstek BLE integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MarstekDataUpdateCoordinator
from .entity import EntityBinding, EntityPlatform
from .product_entity_platform import setup_product_entity_platform


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up declarative Marstek BLE binary sensors from a config entry."""

    coordinator = entry.runtime_data
    setup_product_entity_platform(
        coordinator,
        entry,
        async_add_entities,
        EntityPlatform.BINARY_SENSOR,
        MarstekBinarySensor,
    )


class MarstekBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Marstek binary sensor."""

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str | EntityBinding,
        name: str | None = None,
        value_fn=None,
        device_class: BinarySensorDeviceClass | None = None,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize a declarative or legacy binary sensor."""

        super().__init__(coordinator)
        self._binding: EntityBinding | None = key if isinstance(key, EntityBinding) else None
        self._legacy_value_fn = value_fn

        if self._binding is not None:
            description = self._binding.description
            self._key = self._binding.unique_key
            self._attr_entity_description = description
            self._attr_name = description.name
            self._attr_has_entity_name = True
            self._attr_device_class = getattr(description, "device_class", None)
            self._attr_entity_category = getattr(description, "entity_category", None)
        else:
            self._key = key
            self._attr_name = name
            self._attr_has_entity_name = True
            self._attr_device_class = device_class
            self._attr_entity_category = entity_category

        self._attr_unique_id = f"{entry.entry_id}_{self._key}"

    @property
    def available(self) -> bool:
        """Return whether this entity and any repeated record are present."""

        if not (super().available and self.coordinator.data is not None):
            return False
        return self._binding is None or self._binding.is_present(self.coordinator.data)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""

        if self._binding is not None:
            return self._binding.value_from(self.coordinator.data)
        return self._legacy_value_fn(self.coordinator.data)

    @property
    def device_info(self):
        """Return product-aware device information."""

        if self._binding is None:
            return {
                "identifiers": {(DOMAIN, self.coordinator.ble_device.address)},
                "connections": {
                    (CONNECTION_BLUETOOTH, self.coordinator.ble_device.address)
                },
                "name": self.coordinator.device_name,
                "manufacturer": "Marstek",
                "model": "Venus E",
            }

        device = self._binding.device
        main_identifier = self.coordinator.address
        info = {
            "identifiers": {(DOMAIN, device.identifier(main_identifier))},
            "name": device.name or self.coordinator.device_name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        if device.parent_key is None:
            info["connections"] = {(CONNECTION_BLUETOOTH, main_identifier)}
        else:
            info["via_device"] = (DOMAIN, main_identifier)
        return info
