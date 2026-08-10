"""Declarative Home Assistant entity and device planning.

Sensor and binary-sensor platforms consume these bindings at runtime. Product
profiles remain the source of entity metadata and repeated child-device topology.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields, is_dataclass, replace
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorEntityDescription

from .schema import (
    DataPath,
    RepeatedSectionSpec,
    get_field_entities,
    get_indexed_entities,
    get_repeated_section,
)

EntityDescription = SensorEntityDescription | BinarySensorEntityDescription
ValueGetter = Callable[[Any], Any]


class EntityPlatform(StrEnum):
    """Platforms represented by product entity metadata."""

    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"


@dataclass(frozen=True, slots=True)
class FieldEntitySpec:
    """Attach an entity description to one dataclass field."""

    platform: EntityPlatform
    description: EntityDescription


@dataclass(frozen=True, slots=True)
class IndexedEntitySpec:
    """Expand one sequence-valued field into several entities."""

    platform: EntityPlatform
    count: int
    description_factory: Callable[[int], SensorEntityDescription] = field(
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class DerivedEntitySpec:
    """Describe an entity calculated from several fields."""

    platform: EntityPlatform
    description: EntityDescription
    value_fn: ValueGetter = field(repr=False, compare=False)
    stale_paths: tuple[DataPath, ...] = ()


@dataclass(frozen=True, slots=True)
class ProductDeviceSpec:
    """Primary Home Assistant device metadata."""

    manufacturer: str
    model: str
    model_id: str | None = None


@dataclass(frozen=True, slots=True)
class RepeatedChildDeviceSpec:
    """Map repeated records to stable child devices."""

    key_prefix: str
    model: str
    name_factory: Callable[[int], str] = field(repr=False, compare=False)
    identifier_factory: Callable[[int], str] = field(repr=False, compare=False)
    model_id: str | None = None


@dataclass(frozen=True, slots=True)
class DeviceBinding:
    """One primary or child device produced by an entity plan."""

    key: str
    name: str | None
    manufacturer: str
    model: str
    model_id: str | None = None
    identifier_suffix: str | None = None
    parent_key: str | None = None
    index: int | None = None

    def identifier(self, main_identifier: str) -> str:
        """Return the stable registry identifier."""

        if self.identifier_suffix is None:
            return main_identifier
        return f"{main_identifier}:{self.identifier_suffix}"


@dataclass(frozen=True, slots=True)
class PresenceBinding:
    """Runtime presence check for one repeated item."""

    count_path: DataPath
    index: int
    maximum_count: int

    def is_present(self, data: Any) -> bool:
        """Return whether the indexed item is populated."""

        return self.index < _count(_resolve(data, self.count_path), self.maximum_count)


@dataclass(frozen=True, slots=True)
class EntityBinding:
    """Resolved metadata and value access for one entity."""

    platform: EntityPlatform
    description: EntityDescription
    device: DeviceBinding
    path: DataPath | None = None
    value_fn: ValueGetter | None = field(default=None, repr=False, compare=False)
    stale_paths: tuple[DataPath, ...] = ()
    presence: PresenceBinding | None = None
    repeated_key: str | None = None

    @property
    def unique_key(self) -> str:
        """Return the product-local unique-ID suffix."""

        if self.device.key != "main":
            return f"{self.device.key}_{self.description.key}"
        if self.repeated_key is not None:
            return f"{self.repeated_key}_{self.description.key}"
        return self.description.key

    def value_from(self, data: Any) -> Any:
        """Read or calculate the entity value."""

        if self.value_fn is not None:
            return self.value_fn(data)
        if self.path is None:
            raise ValueError("Entity binding has no value source")
        return _resolve(data, self.path)

    def is_present(self, data: Any) -> bool:
        """Return whether the entity's repeated item is present."""

        return self.presence is None or self.presence.is_present(data)


@dataclass(frozen=True, slots=True)
class ExpansionChange:
    """A detected increase in populated repeated product records."""

    path: DataPath
    configured_count: int
    discovered_count: int
    maximum_count: int
    issue_id: str
    translation_key: str = "expansion_count_increased"


@dataclass(frozen=True, slots=True)
class EntityPlan:
    """Frozen view of the currently configured devices and entities."""

    devices: tuple[DeviceBinding, ...]
    entities: tuple[EntityBinding, ...]
    repeated_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "repeated_counts", MappingProxyType(dict(self.repeated_counts)))


@dataclass(frozen=True, slots=True)
class ProductProfile:
    """Single source of truth for one product family."""

    product_id: str
    device: ProductDeviceSpec
    data_type: type[Any]
    packets: tuple[Any, ...]
    discovery_prefixes: tuple[str, ...] = ()
    derived_entities: tuple[DerivedEntitySpec, ...] = ()

    def create_data(self) -> Any:
        """Create an empty cumulative data object."""

        return self.data_type()

    def build_entity_plan(
        self,
        data: Any,
        *,
        configured_repeated_counts: Mapping[str, int] | None = None,
    ) -> EntityPlan:
        """Build devices and entities for setup or explicit reconfiguration."""

        if not isinstance(data, self.data_type):
            raise TypeError(f"{self.product_id} expects {self.data_type.__name__}")

        main = DeviceBinding(
            key="main",
            name=None,
            manufacturer=self.device.manufacturer,
            model=self.device.model,
            model_id=self.device.model_id,
        )
        devices = {main.key: main}
        entities: list[EntityBinding] = []
        counts: dict[str, int] = {}
        _collect(
            root=data,
            current=data,
            path=(),
            device=main,
            presence=None,
            name_prefix=None,
            key_prefix=None,
            devices=devices,
            entities=entities,
            counts=counts,
            configured_counts=configured_repeated_counts or {},
        )
        for spec in self.derived_entities:
            entities.append(
                EntityBinding(
                    platform=spec.platform,
                    description=spec.description,
                    device=main,
                    value_fn=spec.value_fn,
                    stale_paths=spec.stale_paths,
                )
            )
        return EntityPlan(tuple(devices.values()), tuple(entities), counts)

    def detect_expansion_increases(
        self,
        data: Any,
        plan: EntityPlan,
    ) -> tuple[ExpansionChange, ...]:
        """Compare current repeated counts with a previously generated plan."""

        changes: list[ExpansionChange] = []
        _find_increases(data, data, (), plan.repeated_counts, self.product_id, changes)
        return tuple(changes)


def sensor_entity(**kwargs: Any) -> FieldEntitySpec:
    """Create a sensor field specification."""

    return FieldEntitySpec(EntityPlatform.SENSOR, SensorEntityDescription(**kwargs))


def binary_sensor_entity(**kwargs: Any) -> FieldEntitySpec:
    """Create a binary-sensor field specification."""

    return FieldEntitySpec(
        EntityPlatform.BINARY_SENSOR,
        BinarySensorEntityDescription(**kwargs),
    )


def indexed_sensor_entities(
    count: int,
    factory: Callable[[int], SensorEntityDescription],
) -> IndexedEntitySpec:
    """Create an indexed sensor expansion."""

    return IndexedEntitySpec(EntityPlatform.SENSOR, count, factory)


def derived_sensor(
    *,
    description: SensorEntityDescription,
    value_fn: ValueGetter,
    stale_paths: tuple[DataPath, ...] = (),
) -> DerivedEntitySpec:
    """Create a derived sensor specification."""

    return DerivedEntitySpec(EntityPlatform.SENSOR, description, value_fn, stale_paths)


def derived_binary_sensor(
    *,
    description: BinarySensorEntityDescription,
    value_fn: ValueGetter,
    stale_paths: tuple[DataPath, ...] = (),
) -> DerivedEntitySpec:
    """Create a derived binary-sensor specification."""

    return DerivedEntitySpec(
        EntityPlatform.BINARY_SENSOR,
        description,
        value_fn,
        stale_paths,
    )


def _collect(
    *,
    root: Any,
    current: Any,
    path: DataPath,
    device: DeviceBinding,
    presence: PresenceBinding | None,
    name_prefix: str | None,
    key_prefix: str | None,
    devices: dict[str, DeviceBinding],
    entities: list[EntityBinding],
    counts: dict[str, int],
    configured_counts: Mapping[str, int],
) -> None:
    for data_field in fields(current):
        field_path = (*path, data_field.name)
        value = getattr(current, data_field.name)

        for spec in get_field_entities(data_field):
            description = _prefixed(spec.description, name_prefix)
            entities.append(
                EntityBinding(
                    spec.platform,
                    description,
                    device,
                    path=field_path,
                    stale_paths=(field_path,),
                    presence=presence,
                    repeated_key=key_prefix,
                )
            )

        for spec in get_indexed_entities(data_field):
            if len(value) < spec.count:
                raise ValueError(f"{_path(field_path)} has fewer items than configured")
            for index in range(spec.count):
                item_path = (*field_path, index)
                description = _prefixed(spec.description_factory(index), name_prefix)
                indexed_key = f"{key_prefix}_{index}" if key_prefix else f"{_path(field_path)}_{index}"
                entities.append(
                    EntityBinding(
                        spec.platform,
                        description,
                        device,
                        path=item_path,
                        stale_paths=(field_path,),
                        presence=presence,
                        repeated_key=indexed_key,
                    )
                )

        repeated = get_repeated_section(data_field)
        if repeated is not None:
            _collect_repeated(
                root=root,
                parent=current,
                value=value,
                path=field_path,
                parent_device=device,
                parent_presence=presence,
                parent_name=name_prefix,
                parent_key=key_prefix,
                spec=repeated,
                devices=devices,
                entities=entities,
                counts=counts,
                configured_counts=configured_counts,
            )
        elif is_dataclass(value) and not isinstance(value, type):
            _collect(
                root=root,
                current=value,
                path=field_path,
                device=device,
                presence=presence,
                name_prefix=name_prefix,
                key_prefix=key_prefix,
                devices=devices,
                entities=entities,
                counts=counts,
                configured_counts=configured_counts,
            )


def _collect_repeated(
    *,
    root: Any,
    parent: Any,
    value: list[Any],
    path: DataPath,
    parent_device: DeviceBinding,
    parent_presence: PresenceBinding | None,
    parent_name: str | None,
    parent_key: str | None,
    spec: RepeatedSectionSpec,
    devices: dict[str, DeviceBinding],
    entities: list[EntityBinding],
    counts: dict[str, int],
    configured_counts: Mapping[str, int],
) -> None:
    path_name = _path(path)
    discovered = _active_count(parent, spec)
    configured = _count(configured_counts.get(path_name, discovered), spec.count)
    counts[path_name] = configured
    count_path = (*path[:-1], spec.active_count_attribute) if spec.active_count_attribute else None

    for index in range(configured):
        item = value[index]
        presence = parent_presence
        if count_path is not None:
            presence = PresenceBinding(count_path, index, spec.count)

        item_device = parent_device
        item_name = spec.item_name_factory(index) if spec.item_name_factory else parent_name
        item_key = f"{_path(path)}_{index}"
        if parent_key:
            item_key = f"{parent_key}_{item_key}"

        child = spec.child_device
        if child is not None:
            if not isinstance(child, RepeatedChildDeviceSpec):
                raise TypeError("child_device must be RepeatedChildDeviceSpec")
            device_key = f"{child.key_prefix}_{index}"
            item_device = DeviceBinding(
                key=device_key,
                name=child.name_factory(index),
                manufacturer=parent_device.manufacturer,
                model=child.model,
                model_id=child.model_id,
                identifier_suffix=child.identifier_factory(index),
                parent_key=parent_device.key,
                index=index,
            )
            devices[device_key] = item_device
            item_name = None
            item_key = None

        _collect(
            root=root,
            current=item,
            path=(*path, index),
            device=item_device,
            presence=presence,
            name_prefix=item_name,
            key_prefix=item_key,
            devices=devices,
            entities=entities,
            counts=counts,
            configured_counts=configured_counts,
        )


def _find_increases(
    root: Any,
    current: Any,
    path: DataPath,
    configured: Mapping[str, int],
    product_id: str,
    changes: list[ExpansionChange],
) -> None:
    for data_field in fields(current):
        field_path = (*path, data_field.name)
        value = getattr(current, data_field.name)
        spec = get_repeated_section(data_field)
        if spec is not None:
            path_name = _path(field_path)
            discovered = _active_count(current, spec)
            old = configured.get(path_name, discovered)
            if discovered > old:
                changes.append(
                    ExpansionChange(
                        field_path,
                        old,
                        discovered,
                        spec.count,
                        f"{product_id}_{path_name.replace('.', '_')}_expansion_count_increased",
                    )
                )
            for index, item in enumerate(value):
                if is_dataclass(item):
                    _find_increases(root, item, (*field_path, index), configured, product_id, changes)
        elif is_dataclass(value) and not isinstance(value, type):
            _find_increases(root, value, field_path, configured, product_id, changes)


def _active_count(parent: Any, spec: RepeatedSectionSpec) -> int:
    if spec.active_count_attribute is None:
        return spec.count
    return _count(getattr(parent, spec.active_count_attribute), spec.count)


def _count(value: Any, maximum: int) -> int:
    if value is None:
        return 0
    return max(0, min(int(value), maximum))


def _resolve(data: Any, path: DataPath) -> Any:
    value = data
    for part in path:
        value = value[part] if isinstance(part, int) else getattr(value, part)
    return value


def _path(path: DataPath) -> str:
    return ".".join(str(part) for part in path)


def _prefixed(description: EntityDescription, prefix: str | None) -> EntityDescription:
    if prefix is None or description.name is None:
        return description
    return replace(description, name=f"{prefix} {description.name}")
