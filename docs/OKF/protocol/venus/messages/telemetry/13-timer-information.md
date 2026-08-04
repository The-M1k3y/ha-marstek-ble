---
type: BLE Message
title: Venus 0x13 timer information
description: Timer response fields used for adaptive mode and smart-meter status.
tags: [venus, ble, telemetry, timer]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Timer-information parser
---

# Request

Command `0x13` is sent with an empty payload during medium polls.

Minimum response payload length: 45 bytes.

# Payload schema

| Offset | Length   | Type     | Name                       | Unit    | Description                           |
| ------: | -------: | -------- | -------------------------- | ------- | ------------------------------------- |
| `0x00` | 1        | `u8`     | `adaptive_mode_enabled`    | boolean | Nonzero is true.                      |
| `0x01` | 36       | unknown  | unknown                    | —       | Unused bytes through `0x24`.          |
| `0x25` | 1        | `u8`     | `smart_meter_connected`    | boolean | Nonzero is true.                      |
| `0x26` | 2        | `u16 LE` | `adaptive_power_out`       | W       | Raw watt value.                       |
| `0x28` | 5        | unknown  | unknown                    | —       | Unused through `0x2C` in required data. |
| `0x2D` | variable | unknown  | unknown                    | —       | Any remaining suffix is ignored.      |
