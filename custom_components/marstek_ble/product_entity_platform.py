"""Runtime helpers for declarative product entity plans."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import EntityBinding, EntityPlatform
from .product_coordinator import ProductDataUpdateCoordinator

EntityFactory = Callable[[ProductDataUpdateCoordinator, ConfigEntry, EntityBinding], Any]


class ProductEntityManager:
    """Add declarative entities as fixed or repeated product records appear."""

    def __init__(
        self,
        coordinator: ProductDataUpdateCoordinator,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        platform: EntityPlatform,
        factory: EntityFactory,
    ) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._async_add_entities = async_add_entities
        self.platform = platform
        self._factory = factory
        self._known_keys: set[str] = set()

    def sync(self) -> None:
        """Add newly available bindings without removing stable existing entities."""

        data = self.coordinator.data
        if data is None:
            return

        plan = self.coordinator.product.profile.build_entity_plan(data)
        new_entities = []
        new_keys = []
        for binding in plan.entities:
            if binding.platform is not self.platform:
                continue
            if binding.unique_key in self._known_keys:
                continue
            new_entities.append(self._factory(self.coordinator, self.entry, binding))
            new_keys.append(binding.unique_key)

        if new_entities:
            self._async_add_entities(new_entities)
            self._known_keys.update(new_keys)


def setup_product_entity_platform(
    coordinator: ProductDataUpdateCoordinator,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    platform: EntityPlatform,
    factory: EntityFactory,
) -> ProductEntityManager:
    """Create a manager, subscribe it to updates, and populate current entities."""

    manager = ProductEntityManager(
        coordinator,
        entry,
        async_add_entities,
        platform,
        factory,
    )
    unsubscribe = coordinator.async_add_listener(manager.sync)
    entry.async_on_unload(unsubscribe)
    manager.sync()
    return manager
