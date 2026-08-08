"""Shared pytest hooks for repository test environments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def pytest_configure(config) -> None:
    """Expand lightweight entity-description stubs when isolated tests use them."""

    from homeassistant.const import __version__ as ha_version

    if ha_version != "2026.8.0-test":
        return

    from homeassistant.components import binary_sensor as ha_binary_sensor
    from homeassistant.components import sensor as ha_sensor

    @dataclass(frozen=True)
    class SensorEntityDescription:
        key: str = ""
        name: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: Any = None
        state_class: Any = None
        entity_category: Any = None
        suggested_display_precision: int | None = None

    @dataclass(frozen=True)
    class BinarySensorEntityDescription:
        key: str = ""
        name: str | None = None
        device_class: Any = None
        entity_category: Any = None

    ha_sensor.SensorEntityDescription = SensorEntityDescription
    ha_binary_sensor.BinarySensorEntityDescription = BinarySensorEntityDescription
