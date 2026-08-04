---
type: BLE Message
title: Venus 0x09 buzzer and manual mode
description: Dual-use boolean command for buzzer control and manual operating mode.
tags: [venus, ble, control, dual-use]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: switch
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/switch.py
    title: Buzzer switch
  - id: select
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/select.py
    title: Manual-mode selector
---

# Request schema

Command byte: `0x09`.

| Offset | Length | Type | Name      | Unit    | Description                                                                 |
| ------: | -----: | ---- | --------- | ------- | --------------------------------------------------------------------------- |
| `0x00` | 1      | `u8` | `enabled` | boolean | Buzzer sends `0x01`/`0x00`; manual-mode selection sends `0x01`.            |

The payload contains no discriminator between the two meanings; meaning comes from the calling entity. No command-specific response payload is parsed.
