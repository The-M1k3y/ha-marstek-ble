---
type: BLE Message
title: Venus 0x21 meter IP
description: Meter-IP query request and variable-length ASCII response.
tags: [venus, ble, telemetry, network]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: implementation
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Meter-IP parser
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/coordinator.py
    title: Meter-IP request
---

# Request schema

| Offset | Length | Type | Name             | Unit | Description                                                               |
| ------: | -----: | ---- | ---------------- | ---- | ------------------------------------------------------------------------- |
| `0x00` | 1      | `u8` | `query_selector` | —    | Constant `0x0B`; the code does not identify its semantic meaning.         |

# Response schema

| Offset | Length   | Type               | Name       | Unit | Description                                                                  |
| ------: | -------: | ------------------ | ---------- | ---- | ---------------------------------------------------------------------------- |
| `0x00` | variable | ASCII or `FF` fill | `meter_ip` | —    | All `FF` means not set; otherwise ASCII is decoded and edge NULs stripped.   |

There are no fixed internal response offsets. Undecodable bytes are ignored.
