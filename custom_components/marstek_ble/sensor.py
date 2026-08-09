"""Sensor platform for Marstek BLE integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
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

_LOGGER = logging.getLogger(__name__)
VERBOSE_LOGGER = logging.getLogger(f"{__name__}.verbose")
VERBOSE_LOGGER.propagate = False
VERBOSE_LOGGER.setLevel(logging.INFO)
STALE_AFTER_SECONDS = 10 * 60


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up declarative Marstek BLE sensors from a config entry."""

    coordinator = entry.runtime_data
    setup_product_entity_platform(
        coordinator,
        entry,
        async_add_entities,
        EntityPlatform.SENSOR,
        MarstekSensor,
    )

    # Preserve the legacy Venus-only presentation sensor until it is represented
    # directly in the Venus product profile.
    if coordinator.product.product_id == "venus":
        async_add_entities(
            [
                MarstekTextSensor(
                    coordinator,
                    entry,
                    "battery_state",
                    "Battery State",
                    lambda data: (
                        "charging"
                        if data.battery_voltage is not None
                        and data.battery_current is not None
                        and data.battery_voltage * data.battery_current > 5
                        else "discharging"
                        if data.battery_voltage is not None
                        and data.battery_current is not None
                        and data.battery_voltage * data.battery_current < -5
                        else "inactive"
                    ),
                    stale_fields=["battery_voltage", "battery_current"],
                )
            ]
        )


class MarstekSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Marstek sensor.

    The legacy constructor remains supported for regression compatibility while
    live setup now supplies an :class:`EntityBinding` from the product profile.
    """

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str | EntityBinding,
        name: str | None = None,
        value_fn=None,
        unit: str | None = None,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
        entity_category: EntityCategory | None = None,
        suggested_display_precision: int | None = None,
        stale_fields: list[str] | None = None,
    ) -> None:
        """Initialize a declarative or legacy sensor."""

        super().__init__(coordinator)
        self._binding: EntityBinding | None = key if isinstance(key, EntityBinding) else None
        self._legacy_value_fn = value_fn

        if self._binding is not None:
            description = self._binding.description
            self._key = self._binding.unique_key
            self._stale_fields: tuple[Any, ...] = self._binding.stale_paths
            self._attr_entity_description = description
            self._attr_name = description.name
            self._attr_has_entity_name = True
            self._attr_native_unit_of_measurement = getattr(
                description, "native_unit_of_measurement", None
            )
            self._attr_device_class = getattr(description, "device_class", None)
            self._attr_state_class = getattr(description, "state_class", None)
            self._attr_entity_category = getattr(description, "entity_category", None)
            precision = getattr(description, "suggested_display_precision", None)
            if precision is not None:
                self._attr_suggested_display_precision = precision
        else:
            self._key = key
            self._stale_fields = tuple(stale_fields or [key])
            self._attr_name = name
            self._attr_has_entity_name = True
            self._attr_native_unit_of_measurement = unit
            self._attr_device_class = device_class
            self._attr_state_class = state_class
            self._attr_entity_category = entity_category
            if suggested_display_precision is not None:
                self._attr_suggested_display_precision = suggested_display_precision

        self._attr_unique_id = f"{entry.entry_id}_{self._key}"

    def _handle_coordinator_update(self) -> None:
        """Handle updated data with telemetry for debugging staleness."""

        value = self.native_value
        meta = self._get_representative_metadata()
        VERBOSE_LOGGER.debug(
            "[%s/%s] Sensor update %s=%s (source=%s ts=%s age=%.1fs payload=%s)",
            self.coordinator.device_name,
            self.coordinator.address,
            self._key,
            value,
            meta.get("command_hex") if meta else "unknown",
            meta.get("timestamp") if meta else "unknown",
            meta.get("age_seconds", -1) if meta else -1,
            meta.get("payload_hex") if meta else "unknown",
        )
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return whether the sensor currently has a valid product binding."""

        if not (super().available and self.coordinator.data is not None):
            return False
        if self._binding is not None and not self._binding.is_present(self.coordinator.data):
            return False
        age = self._stale_age_seconds()
        return age is None or age <= STALE_AFTER_SECONDS

    @property
    def native_value(self):
        """Return the state of the sensor."""

        if self._binding is not None:
            return self._binding.value_from(self.coordinator.data)
        return self._legacy_value_fn(self.coordinator.data)

    def _stale_age_seconds(self) -> float | None:
        """Return the oldest dependency age in seconds if available."""

        data = self.coordinator.data
        if data is None:
            return None
        getter = getattr(data, "get_field_metadata", None)
        if getter is None:
            return None

        ages: list[float] = []
        for field in self._stale_fields:
            meta = getter(field)
            if not meta or meta.get("age_seconds") is None:
                continue
            ages.append(meta["age_seconds"])
        return max(ages) if ages else None

    def _get_representative_metadata(self) -> dict | None:
        """Return metadata for logging from the first available field."""

        data = self.coordinator.data
        if data is None:
            return None
        getter = getattr(data, "get_field_metadata", None)
        if getter is None:
            return None
        for field in self._stale_fields:
            meta = getter(field)
            if meta:
                return meta
        return None

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


class MarstekTextSensor(MarstekSensor):
    """Legacy text-sensor constructor retained for existing callers and tests."""

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        value_fn,
        entity_category: EntityCategory | None = None,
        stale_fields: list[str] | None = None,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            key,
            name,
            value_fn,
            entity_category=entity_category,
            stale_fields=stale_fields,
        )

    @property
    def native_value(self):
        """Return the legacy text state as a string."""

        value = super().native_value
        return str(value) if value is not None else None
