"""Runtime parsing and polling behavior for Marstek Jupiter-C Plus."""

from __future__ import annotations

from ..product_runtime import PollCommand, ProductRuntime
from ..schema import DataPath
from .jupiter import JUPITER_PROFILE, JupiterData, JupiterPackets


def _parse_device_information(payload: bytes, data: JupiterData) -> tuple[DataPath, ...]:
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


def _parse_wifi_ssid(payload: bytes, data: JupiterData) -> tuple[DataPath, ...]:
    """Parse the configured Jupiter Wi-Fi SSID."""

    try:
        ssid = payload.decode("utf-8")
    except UnicodeDecodeError:
        return ()
    data.identity.wifi_ssid = ssid.rstrip("\x00")
    return (("identity", "wifi_ssid"),)


JUPITER_RUNTIME = ProductRuntime(
    profile=JUPITER_PROFILE,
    fast_poll=(
        PollCommand(JupiterPackets.RUNTIME_INFORMATION.command, delay=0.1),
        PollCommand(JupiterPackets.DETAILED_TELEMETRY.command, delay=0.1),
    ),
    medium_poll=(
        PollCommand(JupiterPackets.UNRESOLVED_STATUS.command),
        PollCommand(JupiterPackets.WIFI_SSID.command),
        PollCommand(JupiterPackets.RAW_STATUS_22.command),
        PollCommand(JupiterPackets.RAW_STATUS_21.command, b"\x0b"),
        PollCommand(JupiterPackets.RAW_STATUS_24.command),
        PollCommand(JupiterPackets.DEVICE_INFORMATION.command),
        PollCommand(JupiterPackets.EVENT_HISTORY.command),
    ),
    payload_parsers={
        JupiterPackets.DEVICE_INFORMATION.command: _parse_device_information,
        JupiterPackets.WIFI_SSID.command: _parse_wifi_ssid,
    },
)
