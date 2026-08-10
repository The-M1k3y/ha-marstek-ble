"""Runtime helpers for declarative product entity plans."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import EntityBinding, EntityPlatform
from .product_coordinator import ProductDataUpdateCoordinator
from .products import VENUS_RUNTIME

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

            # Fixed indexed scalar fields already provide a distinct entity key
            # for each index (for example Venus ``cell_1_voltage``). The planner's
            # path-derived repeated key is useful internally, but exposing it in
            # Home Assistant would change established entity unique IDs. Repeated
            # product records keep their topology key because their path ends in a
            # field name rather than the indexed scalar itself.
            live_binding = binding
            if (
                binding.device.key == "main"
                and binding.repeated_key is not None
                and binding.path
                and isinstance(binding.path[-1], int)
            ):
                index = binding.path[-1]
                field_path = ".".join(str(part) for part in binding.path[:-1])
                if binding.repeated_key == f"{field_path}_{index}":
                    live_binding = replace(binding, repeated_key=None)

            unique_key = live_binding.unique_key
            if unique_key in self._known_keys:
                continue
            new_entities.append(
                self._factory(self.coordinator, self.entry, live_binding)
            )
            new_keys.append(unique_key)

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

    # Compatibility callers created before product-aware coordinators existed may
    # still supply VenusData without a ``product`` attribute. Treat those as the
    # historical Venus runtime while keeping real product coordinators explicit.
    if not hasattr(coordinator, "product"):
        coordinator.product = VENUS_RUNTIME

    manager = ProductEntityManager(
        coordinator,
        entry,
        async_add_entities,
        platform,
        factory,
    )

    add_listener = getattr(coordinator, "async_add_listener", None)
    if add_listener is not None:
        unsubscribe = add_listener(manager.sync)
        async_on_unload = getattr(entry, "async_on_unload", None)
        if async_on_unload is not None:
            async_on_unload(unsubscribe)

    manager.sync()
    return manager
