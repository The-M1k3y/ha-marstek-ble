---
type: BLE Message
title: Venus 0x1A configuration data
description: Configuration response layout consumed by the integration.
tags: [venus, ble, telemetry, configuration]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Configuration parser
---

# Request

Command `0x1A` is sent with an empty payload during medium polls.

Minimum response payload length: 17 bytes.

# Payload schema

| Offset | Length   | Type    | Name            | Unit | Description                                    |
| ------: | -------: | ------- | --------------- | ---- | ---------------------------------------------- |
| `0x00` | 1        | `u8`    | `config_mode`   | —    | Used as charge-mode readback.                  |
| `0x01` | 3        | unknown | unknown         | —    | Unused bytes through `0x03`.                   |
| `0x04` | 1        | `s8`    | `config_status` | —    | Signed raw status value.                       |
| `0x05` | 11       | unknown | unknown         | —    | Unused bytes through `0x0F`.                   |
| `0x10` | 1        | `u8`    | `config_value`  | —    | Raw configuration value.                       |
| `0x11` | variable | unknown | unknown         | —    | Any remaining suffix beyond 17 bytes is ignored. |
