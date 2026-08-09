"""Lightweight dependency stubs for isolated unit tests."""
from __future__ import annotations

import copy
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _module(name: str, *, package: bool = False) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    if package:
        mod.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = mod
    if "." in name:
        parent_name, child = name.rsplit(".", 1)
        parent = _module(parent_name, package=True)
        setattr(parent, child, mod)
    return mod


# --- voluptuous -----------------------------------------------------------
vol = _module("voluptuous")


class Required:
    def __init__(self, key: Any, default: Any = None) -> None:
        self.schema = key
        self.default = default

    def __hash__(self) -> int:
        return hash(self.schema)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Required) and self.schema == other.schema


class In:
    def __init__(self, values: Any) -> None:
        self.container = values

    def __call__(self, value: Any) -> Any:
        if value not in self.container:
            raise ValueError(value)
        return value


class Schema:
    def __init__(self, schema: Any) -> None:
        self.schema = schema

    def __call__(self, value: Any) -> Any:
        if not isinstance(self.schema, dict):
            return value
        result = dict(value)
        for key, validator in self.schema.items():
            actual = key.schema if isinstance(key, Required) else key
            if actual not in result:
                if isinstance(key, Required) and key.default is not None:
                    result[actual] = key.default
                else:
                    raise ValueError(actual)
            if callable(validator):
                validator(result[actual])
        return result


vol.Required = Required
vol.In = In
vol.Schema = Schema

# --- bleak ----------------------------------------------------------------
_module("bleak", package=True)
_module("bleak.backends", package=True)
bleak_device = _module("bleak.backends.device")
bleak_exc = _module("bleak.exc")


class BLEDevice:
    def __init__(self, address: str, name: str | None = None) -> None:
        self.address = address
        self.name = name


class BleakError(Exception):
    pass


bleak_device.BLEDevice = BLEDevice
bleak_exc.BleakError = BleakError

bleak_retry = _module("bleak_retry_connector")


class BleakClientWithServiceCache:
    pass


async def establish_connection(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("establish_connection must be mocked")


bleak_retry.BleakClientWithServiceCache = BleakClientWithServiceCache
bleak_retry.establish_connection = establish_connection

# --- Home Assistant -------------------------------------------------------
ha = _module("homeassistant", package=True)
ha_components = _module("homeassistant.components", package=True)
ha_helpers = _module("homeassistant.helpers", package=True)

ha_const = _module("homeassistant.const")
ha_const.CONF_ADDRESS = "address"
ha_const.CONF_NAME = "name"
ha_const.PERCENTAGE = "%"
ha_const.__version__ = "2026.8.0-test"


class Platform:
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    BUTTON = "button"
    SWITCH = "switch"
    SELECT = "select"


class UnitOfElectricCurrent:
    AMPERE = "A"


class UnitOfElectricPotential:
    VOLT = "V"


class UnitOfEnergy:
    KILO_WATT_HOUR = "kWh"
    WATT_HOUR = "Wh"


class UnitOfFrequency:
    HERTZ = "Hz"


class UnitOfPower:
    WATT = "W"


class UnitOfTemperature:
    CELSIUS = "°C"


class UnitOfTime:
    HOURS = "h"


for name, value in {
    "Platform": Platform,
    "UnitOfElectricCurrent": UnitOfElectricCurrent,
    "UnitOfElectricPotential": UnitOfElectricPotential,
    "UnitOfEnergy": UnitOfEnergy,
    "UnitOfFrequency": UnitOfFrequency,
    "UnitOfPower": UnitOfPower,
    "UnitOfTemperature": UnitOfTemperature,
    "UnitOfTime": UnitOfTime,
}.items():
    setattr(ha_const, name, value)

ha_core = _module("homeassistant.core")


class HomeAssistant:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.config_entries: Any = None
        self._ble_devices: dict[str, BLEDevice] = {}
        self._discovered_service_info: list[Any] = []


class CoreState:
    running = "running"


def callback(func):
    return func


ha_core.HomeAssistant = HomeAssistant
ha_core.CoreState = CoreState
ha_core.callback = callback

ha_exceptions = _module("homeassistant.exceptions")


class ConfigEntryNotReady(Exception):
    pass


class HomeAssistantError(Exception):
    pass


ha_exceptions.ConfigEntryNotReady = ConfigEntryNotReady
ha_exceptions.HomeAssistantError = HomeAssistantError

ha_config_entries = _module("homeassistant.config_entries")


class ConfigEntry:
    pass


class ConfigFlow:
    def __init_subclass__(cls, domain: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.DOMAIN = domain

    async def async_set_unique_id(
        self, unique_id: str, *, raise_on_progress: bool = True
    ) -> None:
        self._unique_id = unique_id
        self._raise_on_progress = raise_on_progress

    def _abort_if_unique_id_configured(self) -> None:
        if getattr(self, "_configured_unique", False):
            raise RuntimeError("already_configured")

    def _async_current_entries(self) -> list[Any]:
        return list(getattr(self, "_current_entries", []))

    def _async_current_ids(self) -> set[str]:
        return set(getattr(self, "_current_ids", set()))

    def async_abort(self, *, reason: str) -> dict[str, Any]:
        return {"type": "abort", "reason": reason}

    def async_create_entry(self, *, title: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Any,
        description_placeholders: dict[str, str] | None = None,
        errors: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "description_placeholders": description_placeholders,
            "errors": errors or {},
        }

    def _set_confirm_only(self) -> None:
        self._confirm_only = True


class OptionsFlow:
    def async_create_entry(self, *, title: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, *, step_id: str, data_schema: Any) -> dict[str, Any]:
        return {"type": "form", "step_id": step_id, "data_schema": data_schema}


ha_config_entries.ConfigEntry = ConfigEntry
ha_config_entries.ConfigFlow = ConfigFlow
ha_config_entries.ConfigFlowResult = dict
ha_config_entries.OptionsFlow = OptionsFlow

# Bluetooth
ha_bluetooth = _module("homeassistant.components.bluetooth", package=True)


@dataclass
class BluetoothServiceInfoBleak:
    address: str
    name: str | None
    device: BLEDevice


class BluetoothScanningMode:
    ACTIVE = "active"


class BluetoothChange:
    ADVERTISEMENT = "advertisement"


def async_ble_device_from_address(
    hass: Any, address: str, *, connectable: bool
) -> BLEDevice | None:
    return hass._ble_devices.get(address) or hass._ble_devices.get(address.upper())


def async_discovered_service_info(hass: Any) -> list[BluetoothServiceInfoBleak]:
    return list(hass._discovered_service_info)


ha_bluetooth.BluetoothServiceInfoBleak = BluetoothServiceInfoBleak
ha_bluetooth.BluetoothScanningMode = BluetoothScanningMode
ha_bluetooth.BluetoothChange = BluetoothChange
ha_bluetooth.async_ble_device_from_address = async_ble_device_from_address
ha_bluetooth.async_discovered_service_info = async_discovered_service_info
ha_components.bluetooth = ha_bluetooth

ha_active = _module("homeassistant.components.bluetooth.active_update_coordinator")


class ActiveBluetoothDataUpdateCoordinator:
    def __class_getitem__(cls, item):
        return cls

    def __init__(
        self,
        *,
        hass: Any,
        logger: Any,
        address: str,
        mode: Any,
        needs_poll_method: Any,
        poll_method: Any,
        connectable: bool,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.address = address
        self.mode = mode
        self.needs_poll_method = needs_poll_method
        self.poll_method = poll_method
        self.connectable = connectable
        self.last_poll_successful = True
        self.update_interval = None
        self._listener_updates = 0

    def async_start(self):
        self._started = True

        def unsub():
            self._started = False

        return unsub

    def async_update_listeners(self) -> None:
        self._listener_updates += 1

    def _async_handle_unavailable(self, service_info: Any) -> None:
        self.last_poll_successful = False

    def _async_handle_bluetooth_event(self, service_info: Any, change: Any) -> None:
        self.last_poll_successful = True


ha_active.ActiveBluetoothDataUpdateCoordinator = ActiveBluetoothDataUpdateCoordinator

# Entity base classes and metadata


class _Entity:
    def async_write_ha_state(self) -> None:
        self._write_count = getattr(self, "_write_count", 0) + 1


class CoordinatorEntity(_Entity):
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator

    @property
    def available(self) -> bool:
        return bool(getattr(self.coordinator, "last_update_success", True))

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


ha_update = _module("homeassistant.helpers.update_coordinator")
ha_update.CoordinatorEntity = CoordinatorEntity


class EntityCategory:
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


ha_entity = _module("homeassistant.helpers.entity")
ha_entity.EntityCategory = EntityCategory

ha_sensor = _module("homeassistant.components.sensor")


class SensorEntity(_Entity):
    pass


class SensorDeviceClass:
    VOLTAGE = "voltage"
    CURRENT = "current"
    BATTERY = "battery"
    TEMPERATURE = "temperature"
    POWER = "power"
    ENERGY = "energy"
    ENERGY_STORAGE = "energy_storage"
    DURATION = "duration"
    FREQUENCY = "frequency"


class SensorStateClass:
    MEASUREMENT = "measurement"
    TOTAL_INCREASING = "total_increasing"


@dataclass(frozen=True)
class SensorEntityDescription:
    key: str = ""
    name: str | None = None


ha_sensor.SensorEntity = SensorEntity
ha_sensor.SensorDeviceClass = SensorDeviceClass
ha_sensor.SensorStateClass = SensorStateClass
ha_sensor.SensorEntityDescription = SensorEntityDescription

ha_binary = _module("homeassistant.components.binary_sensor")


class BinarySensorEntity(_Entity):
    pass


class BinarySensorDeviceClass:
    CONNECTIVITY = "connectivity"
    POWER = "power"
    BATTERY_CHARGING = "battery_charging"


@dataclass(frozen=True)
class BinarySensorEntityDescription:
    key: str = ""
    name: str | None = None


ha_binary.BinarySensorEntity = BinarySensorEntity
ha_binary.BinarySensorDeviceClass = BinarySensorDeviceClass
ha_binary.BinarySensorEntityDescription = BinarySensorEntityDescription

for module_name, class_name in [
    ("homeassistant.components.button", "ButtonEntity"),
    ("homeassistant.components.switch", "SwitchEntity"),
    ("homeassistant.components.select", "SelectEntity"),
]:
    mod = _module(module_name)
    setattr(mod, class_name, type(class_name, (_Entity,), {}))

ha_platform = _module("homeassistant.helpers.entity_platform")
ha_platform.AddEntitiesCallback = Any

ha_device_registry = _module("homeassistant.helpers.device_registry")
ha_device_registry.CONNECTION_BLUETOOTH = "bluetooth"


class DeviceRegistry:
    def __init__(self) -> None:
        self.calls = []

    def async_get_or_create(self, **kwargs: Any):
        self.calls.append(kwargs)
        return kwargs


def async_get(hass: Any) -> DeviceRegistry:
    if not hasattr(hass, "_device_registry"):
        hass._device_registry = DeviceRegistry()
    return hass._device_registry


ha_device_registry.async_get = async_get

ha_event = _module("homeassistant.helpers.event")


def async_track_time_interval(hass: Any, action: Any, interval: Any):
    record = {"action": action, "interval": interval, "cancelled": False}
    if not hasattr(hass, "_tracked_intervals"):
        hass._tracked_intervals = []
    hass._tracked_intervals.append(record)

    def unsub():
        record["cancelled"] = True

    return unsub


ha_event.async_track_time_interval = async_track_time_interval

ha_selector = _module("homeassistant.helpers.selector")


@dataclass
class NumberSelectorConfig:
    min: float
    max: float
    mode: str
    unit_of_measurement: str


class NumberSelector:
    def __init__(self, config: NumberSelectorConfig) -> None:
        self.config = config

    def __call__(self, value: Any) -> Any:
        if value < self.config.min or value > self.config.max:
            raise ValueError(value)
        return value


class NumberSelectorMode:
    BOX = "box"


ha_selector.NumberSelectorConfig = NumberSelectorConfig
ha_selector.NumberSelector = NumberSelector
ha_selector.NumberSelectorMode = NumberSelectorMode

ha_redact = _module("homeassistant.helpers.redact")


def async_redact_data(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "**REDACTED**"
                if key in keys
                else async_redact_data(item, keys)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [async_redact_data(item, keys) for item in value]
    return copy.deepcopy(value)


ha_redact.async_redact_data = async_redact_data

# --- aioesphomeapi --------------------------------------------------------
aio = _module("aioesphomeapi", package=True)


class APIClient:
    pass


aio.APIClient = APIClient

aio_ble_defs = _module("aioesphomeapi.ble_defs")
from enum import IntEnum


class BLEConnectionError(IntEnum):
    UNKNOWN = 0
    TIMEOUT = 1


ESP_CONNECTION_ERROR_DESCRIPTION = {
    BLEConnectionError.UNKNOWN: "Unknown error",
    BLEConnectionError.TIMEOUT: "Timeout",
}
aio_ble_defs.BLEConnectionError = BLEConnectionError
aio_ble_defs.ESP_CONNECTION_ERROR_DESCRIPTION = ESP_CONNECTION_ERROR_DESCRIPTION

aio_core = _module("aioesphomeapi.core")


class APIConnectionError(Exception):
    pass


class BluetoothConnectionDroppedError(Exception):
    pass


class TimeoutAPIError(Exception):
    pass


def to_human_readable_address(address: int) -> str:
    raw = f"{address:012X}"[-12:]
    return ":".join(raw[index : index + 2] for index in range(0, 12, 2))


aio_core.APIConnectionError = APIConnectionError
aio_core.BluetoothConnectionDroppedError = BluetoothConnectionDroppedError
aio_core.TimeoutAPIError = TimeoutAPIError
aio_core.to_human_readable_address = to_human_readable_address

aio_model = _module("aioesphomeapi.model")
from enum import IntEnum


@dataclass
class APIVersion:
    major: int
    minor: int


@dataclass
class BluetoothLEAdvertisement:
    address: int
    name: str | None = None
    rssi: int = 0
    address_type: int = 0
    service_uuids: list[str] | None = None


class BluetoothScannerMode:
    ACTIVE = SimpleNamespace(name="ACTIVE")
    PASSIVE = SimpleNamespace(name="PASSIVE")


class BluetoothScannerStateResponse:
    pass


class DeviceInfo:
    pass


aio_model.APIVersion = APIVersion
aio_model.BluetoothLEAdvertisement = BluetoothLEAdvertisement
aio_model.BluetoothScannerMode = BluetoothScannerMode
aio_model.BluetoothScannerStateResponse = BluetoothScannerStateResponse
aio_model.DeviceInfo = DeviceInfo
