---
type: BLE Message
title: Venus 0x0E output and self-consumption
description: Dual-use boolean command for Output 1 and self-consumption operating mode.
tags: [venus, ble, control, dual-use]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: switch
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/switch.py
    title: Output switch
  - id: select
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/select.py
    title: Self-consumption selector
---

# Request schema

Command byte: `0x0E`.

| Offset | Length | Type | Name      | Unit    | Description                                                                  |
| ------: | -----: | ---- | --------- | ------- | ---------------------------------------------------------------------------- |
| `0x00` | 1      | `u8` | `enabled` | boolean | Output sends `0x01`/`0x00`; self-consumption selection sends `0x01`.        |

The payload contains no explicit discriminator between meanings. Output state is read from `out1_active` in `0x03`; operating-mode state is not parsed.
