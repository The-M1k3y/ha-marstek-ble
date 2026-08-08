"""Runtime parsing and polling behavior for Marstek Venus products."""

from __future__ import annotations

import struct

from ..product_runtime import PollCommand, ProductRuntime
from ..schema import DataPath
from .venus import VENUS_PROFILE, VenusData


def _parse_device_information(
    payload: bytes, data: VenusData
) -> tuple[DataPath, ...]:
    text = payload.decode("ascii", errors="ignore")
    values: dict[str, str] = {}
    for pair in text.split(","):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        values[key.strip()] = value.strip()

    section = data.device
    updates: list[DataPath] = []
    mapping = {
        "type": "device_type",
        "id": "device_id",
        "sn": "serial_number",
        "mac": "mac_address",
        "hw": "hardware_version",
    }
    for source_key, attribute in mapping.items():
        if source_key in values:
            setattr(section, attribute, values[source_key])
            updates.append(("device", attribute))

    for source_key in ("dev_ver", "fc_ver", "fw"):
        if source_key in values:
            section.firmware_version = values[source_key]
            if ("device", "firmware_version") not in updates:
                updates.append(("device", "firmware_version"))

    return tuple(updates)


def _parse_wifi_ssid(payload: bytes, data: VenusData) -> tuple[DataPath, ...]:
    data.network.wifi_ssid = payload.decode("ascii", errors="ignore").strip()
    return (("network", "wifi_ssid"),)


def _parse_meter_ip(payload: bytes, data: VenusData) -> tuple[DataPath, ...]:
    if all(value == 0xFF for value in payload):
        meter_ip = "(not set)"
    else:
        meter_ip = payload.decode("ascii", errors="ignore").strip("\x00")
    data.network.meter_ip = meter_ip
    return (("network", "meter_ip"),)


def _parse_network_information(
    payload: bytes, data: VenusData
) -> tuple[DataPath, ...]:
    text = payload.decode("ascii", errors="ignore").strip()
    values: dict[str, str] = {}
    for pair in text.split(","):
        if ":" not in pair:
            continue
        key, value = pair.split(":", 1)
        values[key.strip()] = value.strip()

    section = data.network
    section.network_info = text
    updates: list[DataPath] = [("network", "network_info")]

    mapping = {
        "ip": "ip_address",
        "mask": "subnet_mask",
        "dns": "dns_server",
    }
    for source_key, attribute in mapping.items():
        if source_key in values:
            setattr(section, attribute, values[source_key])
        if getattr(section, attribute) is not None:
            updates.append(("network", attribute))

    gateway = values.get("gate", values.get("gateway"))
    if gateway is not None:
        section.gateway = gateway
    if section.gateway is not None:
        updates.append(("network", "gateway"))

    return tuple(updates)


def _parse_local_api_status(
    payload: bytes, data: VenusData
) -> tuple[DataPath, ...]:
    enabled = "enabled" if payload[0] == 1 else "disabled"
    port = struct.unpack_from("<H", payload, 1)[0]
    data.network.local_api_status = f"{enabled}/{port}"
    return (("network", "local_api_status"),)


VENUS_RUNTIME = ProductRuntime(
    profile=VENUS_PROFILE,
    fast_poll=(
        PollCommand(0x03, delay=0.1),
        PollCommand(0x14, delay=0.1),
    ),
    medium_poll=(
        PollCommand(0x0D),
        PollCommand(0x08),
        PollCommand(0x1A),
        PollCommand(0x22),
        PollCommand(0x21, b"\x0B"),
        PollCommand(0x24),
        PollCommand(0x04),
        PollCommand(0x13),
        PollCommand(0x28),
        PollCommand(0x1C),
    ),
    payload_parsers={
        0x04: _parse_device_information,
        0x08: _parse_wifi_ssid,
        0x21: _parse_meter_ip,
        0x24: _parse_network_information,
        0x28: _parse_local_api_status,
    },
)
