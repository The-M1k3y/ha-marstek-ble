---
type: BLE Message Collection
title: Other Jupiter-C Plus responses
description: Identity, SSID, unresolved status responses, and commands without an observed response schema.
tags: [jupiter, ble, identity, unresolved]
status: draft
source_revision: "17d3211e12989eb428681f5959707e9403e61bf6"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-05T14:19:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter field map
---

# `0x04` device information

The response is comma-separated ASCII `key=value` data. Recognized keys are:

| Key      | Meaning                   |
| -------- | ------------------------- |
| `type`   | Device type / model ID    |
| `id`     | Cloud/device identifier   |
| `mac`    | Bluetooth MAC address     |
| `ems_v`  | EMS firmware version      |
| `inv_v`  | Inverter firmware version |
| `mppt_v` | MPPT firmware version     |
| `bms_v`  | BMS firmware version      |

Unknown keys must not fail the complete packet. Values are not included in this
repository source.

# `0x08` Wi-Fi SSID

The complete payload is an ASCII SSID with configuration-dependent length. No
network name is committed to the repository.

# `0x0D` unresolved status

Payload length: 12 bytes. The Venus interpretation has not been validated for
Jupiter, so no field mapping is defined.

# `0x21`, `0x22`, and `0x24`

Each response is one byte. The Jupiter model retains separate raw destinations
without Home Assistant entities. Venus meanings are not reused.

# `0x1A` and `0x1C`

No response structure is available, so no Jupiter packet schema is defined.
