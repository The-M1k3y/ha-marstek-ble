---
type: BLE Message
title: Venus 0x17 total power
description: Total power setpoint written by the integration.
tags: [venus, ble, control, power]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: button
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/button.py
    title: Total-power button
---

# Request schema

Command byte: `0x17`.

| Offset | Length | Type     | Name    | Unit | Description               |
| ------: | -----: | -------- | ------- | ---- | ------------------------- |
| `0x00` | 2      | `u16 LE` | `power` | W    | Little-endian watt value. |

The code sends `C4 09` for 2500 W. No additional request bytes or command-specific response fields are used.
