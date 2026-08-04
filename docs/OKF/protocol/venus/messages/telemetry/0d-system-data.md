---
type: BLE Message
title: Venus 0x0D system data
description: System-data response layout consumed by the integration.
tags: [venus, ble, telemetry, system]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: System-data parser
---

# Request

For a read, command `0x0D` is sent with an empty payload. The same command byte is also used for [charge-mode writes](../control/0d-charge-mode.md).

Minimum response payload length: 11 bytes.

# Payload schema

| Offset | Length   | Type     | Name              | Unit | Description                       |
| ------: | -------: | -------- | ----------------- | ---- | --------------------------------- |
| `0x00` | 1        | `u8`     | `system_status`   | —    | Raw status value.                 |
| `0x01` | 2        | `u16 LE` | `system_value_1`  | —    | Meaning unknown.                  |
| `0x03` | 2        | `u16 LE` | `system_value_2`  | —    | Meaning unknown.                  |
| `0x05` | 2        | `u16 LE` | `system_value_3`  | —    | Meaning unknown.                  |
| `0x07` | 2        | `u16 LE` | `system_value_4`  | —    | Meaning unknown.                  |
| `0x09` | 2        | `u16 LE` | `system_value_5`  | —    | Meaning unknown.                  |
| `0x0B` | variable | unknown  | unknown           | —    | Any remaining suffix is ignored.  |
