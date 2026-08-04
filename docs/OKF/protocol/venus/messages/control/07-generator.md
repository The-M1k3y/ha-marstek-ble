---
type: BLE Message
title: Venus 0x07 generator
description: Boolean generator control message.
tags: [venus, ble, control]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: switch
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/switch.py
    title: Generator switch
---

# Request schema

Command byte: `0x07`.

| Offset | Length | Type | Name      | Unit    | Description                                              |
| ------: | -----: | ---- | --------- | ------- | -------------------------------------------------------- |
| `0x00` | 1      | `u8` | `enabled` | boolean | `0x01` enables the generator; `0x00` disables it.        |

No additional request bytes are used. No command-specific response payload is parsed.
