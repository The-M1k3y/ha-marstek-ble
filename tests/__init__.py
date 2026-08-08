"""Test package setup for permissive Home Assistant entity descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
