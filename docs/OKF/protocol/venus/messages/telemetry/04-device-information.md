---
type: BLE Message
title: Venus 0x04 device information
description: Variable-length ASCII identity and firmware response parsed by the integration.
tags: [venus, ble, telemetry, identity]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Device information parser
---

# Request

Command `0x04` is sent with an empty payload during medium polls.

# Payload schema

| Offset | Length   | Type      | Name                 | Unit | Description                          |
| ------: | -------: | --------- | -------------------- | ---- | ------------------------------------ |
| `0x00` | variable | ASCII CSV | `device_information` | —    | Comma-separated `key=value` entries. |

Byte offsets inside the payload are variable because keys and values have variable lengths.

# Recognized fields

| Key                       | Name               | Description                                      |
| ------------------------- | ------------------ | ------------------------------------------------ |
| `type`                    | `device_type`      | Device model or type string.                     |
| `id`                      | `device_id`        | Device identifier.                               |
| `sn`                      | `serial_number`    | Serial number.                                   |
| `mac`                     | `mac_address`      | MAC-address string.                              |
| `dev_ver`, `fc_ver`, `fw` | `firmware_version` | Firmware version; later matching keys overwrite. |
| `hw`                      | `hardware_version` | Hardware version.                                |

Unknown keys, entries without `=`, and undecodable bytes are ignored.
