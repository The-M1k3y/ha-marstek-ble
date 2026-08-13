"""Runtime parsing and polling behavior for Marstek Jupiter-C Plus."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from ..product_runtime import PollCommand, ProductRuntime, TrackedProductData
from ..schema import DataPath
from .jupiter import JUPITER_PROFILE, JupiterData, JupiterPackets


_FLAT_PATHS: dict[str, DataPath] = {
    "battery_voltage": ("battery", "voltage"),
    "battery_current": ("battery", "current"),
    "battery_soc": ("runtime", "battery_soc"),
    "battery_soh": ("battery", "soh"),
    "battery_temp": ("battery", "temperature"),
    "design_capacity": ("battery", "rated_capacity"),
    "grid_power": ("runtime", "ac_output_power"),
    "out1_power": ("runtime", "ac_output_power"),
    "daily_energy_discharged": ("energy", "daily_discharge_energy"),
    "monthly_energy_discharged": ("energy", "monthly_discharge_energy"),
    "total_energy_discharged": ("energy", "local_total_discharge_energy"),
    "mosfet_temp": ("battery", "mosfet_temperature"),
    "temp_sensor_1": ("battery", "temp_sensor_1"),
    "temp_sensor_2": ("battery", "temp_sensor_2"),
    "temp_sensor_3": ("battery", "temp_sensor_3"),
    "temp_sensor_4": ("battery", "temp_sensor_4"),
    "bms_version": ("runtime", "bms_firmware_version"),
    "voltage_limit": ("battery", "charge_voltage_limit"),
    "charge_current_limit": ("battery", "charge_current_limit"),
    "discharge_current_limit": ("battery", "discharge_current_limit"),
    "error_code": ("battery", "error_code_1"),
    "warning_code": ("battery", "warning_code_1"),
    "device_type": ("identity", "device_type"),
    "device_id": ("identity", "device_id"),
    "mac_address": ("identity", "mac_address"),
    "wifi_ssid": ("identity", "wifi_ssid"),
    "out1_active": ("runtime", "ac_output_active"),
}

_UNSUPPORTED_LEGACY_FIELDS = frozenset(
    {
        "cell_voltages",
        "config_mode",
        "ct_polling_rate",
        "daily_energy_charged",
        "dns_server",
        "extern1_connected",
        "firmware_version",
        "gateway",
        "hardware_version",
        "ip_address",
        "meter_ip",
        "monthly_energy_charged",
        "mqtt_connected",
        "network_info",
        "power_rating",
        "product_code",
        "runtime_hours",
        "serial_number",
        "smart_meter_connected",
        "subnet_mask",
        "system_status",
        "temp_high",
        "temp_low",
        "total_energy_charged",
        "wifi_connected",
        "work_mode",
    }
)


@dataclass(slots=True)
class RuntimeJupiterData(JupiterData, TrackedProductData):
    """Jupiter data with update tracking and temporary legacy read aliases."""

    field_updates: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)

    def __getattr__(self, name: str) -> Any:
        if name == "solar_power":
            powers = [item.power for item in self.pv_inputs if item.power is not None]
            return sum(powers) if powers else None
        if name == "remaining_capacity":
            soc = self.runtime.battery_soc
            capacity = self.battery.rated_capacity
            return soc / 100 * capacity if soc is not None and capacity is not None else None
        if name == "available_capacity":
            soc = self.runtime.battery_soc
            capacity = self.battery.rated_capacity
            return (100 - soc) / 100 * capacity if soc is not None and capacity is not None else None

        path = _FLAT_PATHS.get(name)
        if path is not None:
            value: Any = self
            for part in path:
                value = getattr(value, part)
            return value

        if name in _UNSUPPORTED_LEGACY_FIELDS:
            return None
        raise AttributeError(name)

    def _metadata_aliases(self, path: DataPath) -> tuple[str, ...]:
        aliases = list(super()._metadata_aliases(path))
        aliases.extend(name for name, candidate in _FLAT_PATHS.items() if candidate == path)
        if path and path[0] == "pv_inputs" and path[-1] == "power":
            aliases.append("solar_power")
        if path in {("runtime", "battery_soc"), ("battery", "rated_capacity")}:
            aliases.extend(("remaining_capacity", "available_capacity"))
        return tuple(dict.fromkeys(aliases))


JUPITER_RUNTIME_PROFILE = replace(JUPITER_PROFILE, data_type=RuntimeJupiterData)


def _parse_device_information(
    payload: bytes, data: RuntimeJupiterData
) -> tuple[DataPath, ...]:
    """Parse comma-separated Jupiter device information."""

    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError:
        return ()

    values: dict[str, str] = {}
    for item in text.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        values[key.strip()] = value.strip()

    updates: list[DataPath] = []
    identity_fields = {
        "type": "device_type",
        "id": "device_id",
        "mac": "mac_address",
    }
    for source_key, attribute in identity_fields.items():
        if source_key in values:
            setattr(data.identity, attribute, values[source_key])
            updates.append(("identity", attribute))

    version_fields = {
        "ems_v": "ems_firmware_version",
        "inv_v": "inverter_firmware_version",
        "mppt_v": "mppt_firmware_version",
        "bms_v": "bms_firmware_version",
    }
    for source_key, attribute in version_fields.items():
        value = values.get(source_key)
        if value is None:
            continue
        try:
            parsed = int(value)
        except ValueError:
            continue
        setattr(data.runtime, attribute, parsed)
        updates.append(("runtime", attribute))

    return tuple(updates)


def _parse_wifi_ssid(
    payload: bytes, data: RuntimeJupiterData
) -> tuple[DataPath, ...]:
    """Parse the configured Jupiter Wi-Fi SSID."""

    try:
        ssid = payload.decode("utf-8")
    except UnicodeDecodeError:
        return ()
    data.identity.wifi_ssid = ssid.rstrip("\x00")
    return (("identity", "wifi_ssid"),)


JUPITER_RUNTIME = ProductRuntime(
    profile=JUPITER_RUNTIME_PROFILE,
    fast_poll=(
        PollCommand(JupiterPackets.RUNTIME_INFORMATION.command, delay=0.1),
        PollCommand(JupiterPackets.DETAILED_TELEMETRY.command, delay=0.1),
    ),
    medium_poll=(
        PollCommand(JupiterPackets.UNRESOLVED_STATUS.command),
        PollCommand(JupiterPackets.WIFI_SSID.command),
        PollCommand(JupiterPackets.DEVICE_INFORMATION.command),
        PollCommand(JupiterPackets.EVENT_HISTORY.command),
    ),
    payload_parsers={
        JupiterPackets.DEVICE_INFORMATION.command: _parse_device_information,
        JupiterPackets.WIFI_SSID.command: _parse_wifi_ssid,
    },
)
