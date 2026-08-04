---
type: BLE Message
title: Venus 0x15 power mode
description: Power-mode value written by fixed 800 W and 2500 W buttons.
tags: [venus, ble, control, power]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: button
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/button.py
    title: Power-mode buttons
---

# Request schema

Command byte: `0x15`.

| Offset | Length | Type     | Name    | Unit | Description                   |
| ------: | -----: | -------- | ------- | ---- | ----------------------------- |
| `0x00` | 2      | `u16 LE` | `power` | W    | Little-endian watt value.     |

The code sends `20 03` for 800 W and `C4 09` for 2500 W. No additional request bytes or command-specific response fields are used.
