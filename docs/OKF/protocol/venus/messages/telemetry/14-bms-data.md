---
type: BLE Message
title: Venus 0x14 BMS data
description: Battery-management response layout used by the integration.
tags: [venus, ble, telemetry, bms]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: BMS payload parser
---

# Request

Command `0x14` is sent with an empty payload during every fast poll.

Minimum response payload length: 80 bytes.

# Payload schema

| Offset | Length   | Type     | Name                      | Unit | Description                                      |
| ------: | -------: | -------- | ------------------------- | ---- | ------------------------------------------------ |
| `0x00` | 2        | `u16 LE` | `bms_version`             | —    | Raw version value.                               |
| `0x02` | 2        | `u16 LE` | `voltage_limit`           | V    | Divide by 10.                                    |
| `0x04` | 2        | `u16 LE` | `charge_current_limit`    | A    | Divide by 10.                                    |
| `0x06` | 2        | `s16 LE` | `discharge_current_limit` | A    | Divide by 10.                                    |
| `0x08` | 2        | `u16 LE` | `battery_soc`             | %    | Exposed without scaling.                         |
| `0x0A` | 2        | `u16 LE` | `battery_soh`             | %    | Exposed without scaling.                         |
| `0x0C` | 2        | `u16 LE` | `design_capacity`         | Wh   | Exposed without scaling.                         |
| `0x0E` | 2        | `u16 LE` | `battery_voltage`         | V    | Divide by 100.                                   |
| `0x10` | 2        | `s16 LE` | `battery_current`         | A    | Divide by 10.                                    |
| `0x12` | 2        | `u16 LE` | `battery_temp`            | °C   | Exposed without scaling.                         |
| `0x14` | 6        | unknown  | unknown                   | —    | Unused bytes through `0x19`.                     |
| `0x1A` | 2        | `u16 LE` | `error_code`              | —    | Raw integer or bitfield.                         |
| `0x1C` | 4        | `u32 LE` | `warning_code`            | —    | Raw integer or bitfield.                         |
| `0x20` | 4        | `u32 LE` | `runtime_hours`           | h    | Input milliseconds divided by 3,600,000.         |
| `0x24` | 2        | unknown  | unknown                   | —    | Unused bytes through `0x25`.                     |
| `0x26` | 2        | `u16 LE` | `mosfet_temp`             | °C   | Exposed without scaling.                         |
| `0x28` | 2        | `u16 LE` | `temp_sensor_1`           | °C   | Exposed without scaling.                         |
| `0x2A` | 2        | `u16 LE` | `temp_sensor_2`           | °C   | Exposed without scaling.                         |
| `0x2C` | 2        | `u16 LE` | `temp_sensor_3`           | °C   | Exposed without scaling.                         |
| `0x2E` | 2        | `u16 LE` | `temp_sensor_4`           | °C   | Exposed without scaling.                         |
| `0x30` | 2        | `u16 LE` | `cell_1_voltage`          | V    | Divide by 1000.                                  |
| `0x32` | 2        | `u16 LE` | `cell_2_voltage`          | V    | Divide by 1000.                                  |
| `0x34` | 2        | `u16 LE` | `cell_3_voltage`          | V    | Divide by 1000.                                  |
| `0x36` | 2        | `u16 LE` | `cell_4_voltage`          | V    | Divide by 1000.                                  |
| `0x38` | 2        | `u16 LE` | `cell_5_voltage`          | V    | Divide by 1000.                                  |
| `0x3A` | 2        | `u16 LE` | `cell_6_voltage`          | V    | Divide by 1000.                                  |
| `0x3C` | 2        | `u16 LE` | `cell_7_voltage`          | V    | Divide by 1000.                                  |
| `0x3E` | 2        | `u16 LE` | `cell_8_voltage`          | V    | Divide by 1000.                                  |
| `0x40` | 2        | `u16 LE` | `cell_9_voltage`          | V    | Divide by 1000.                                  |
| `0x42` | 2        | `u16 LE` | `cell_10_voltage`         | V    | Divide by 1000.                                  |
| `0x44` | 2        | `u16 LE` | `cell_11_voltage`         | V    | Divide by 1000.                                  |
| `0x46` | 2        | `u16 LE` | `cell_12_voltage`         | V    | Divide by 1000.                                  |
| `0x48` | 2        | `u16 LE` | `cell_13_voltage`         | V    | Divide by 1000.                                  |
| `0x4A` | 2        | `u16 LE` | `cell_14_voltage`         | V    | Divide by 1000.                                  |
| `0x4C` | 2        | `u16 LE` | `cell_15_voltage`         | V    | Divide by 1000.                                  |
| `0x4E` | 2        | `u16 LE` | `cell_16_voltage`         | V    | Divide by 1000.                                  |
| `0x50` | variable | unknown  | unknown                   | —    | Any remaining suffix beyond 80 bytes is ignored. |
