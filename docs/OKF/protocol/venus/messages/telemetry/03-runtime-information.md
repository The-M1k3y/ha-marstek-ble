---
type: BLE Message
title: Venus 0x03 runtime information
description: Runtime response fields consumed by the integration, including overlapping interpretations and unknown regions.
tags: [venus, ble, telemetry, runtime]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: device
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Runtime payload parser
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/coordinator.py
    title: Runtime polling
---

# Request

The coordinator sends command `0x03` with an empty payload during every fast poll.

# Response requirements

The parser rejects payloads shorter than 37 bytes. Payloads from 37 through 59 bytes use a limited short-format branch. Payloads of at least 60 bytes use the baseline long branch, and payloads of at least 100 bytes additionally parse the long-format power and energy fields.

# Schema

| Offset | Length   | Type        | Name                        | Unit    | Description                                                                    |
| ------: | -------: | ----------- | --------------------------- | ------- | ------------------------------------------------------------------------------ |
| `0x00` | 2        | `s16 LE`    | `grid_power`                | W       | Used only when payload length is at least 100 bytes.                           |
| `0x02` | 2        | `s16 LE`    | `solar_power`               | W       | Used only when payload length is at least 100 bytes.                           |
| `0x04` | 1        | `u8`        | `work_mode`                 | —       | Raw operating-mode value; long payload only.                                  |
| `0x05` | 7        | unknown     | unknown                     | —       | Unused bytes through `0x0B`.                                                   |
| `0x0C` | 2        | `u16 LE`    | `product_code`              | —       | Raw product identifier; long payload only.                                    |
| `0x0E` | 4        | `u32 LE`    | `daily_energy_charged`      | kWh     | Divide by 100; long payload only.                                              |
| `0x0F` | 1        | bitfield    | `wifi_connected`            | boolean | Bit 0; overlaps the four-byte field beginning at `0x0E`.                      |
| `0x0F` | 1        | bitfield    | `mqtt_connected`            | boolean | Bit 1; overlaps the four-byte field beginning at `0x0E`.                      |
| `0x10` | 1        | `u8`        | `out1_active`               | boolean | Nonzero is true; overlaps the four-byte field beginning at `0x0E`.            |
| `0x11` | 1        | unknown     | unknown                     | —       | Unused byte; also part of the four-byte field beginning at `0x0E`.            |
| `0x12` | 4        | `u32 LE`    | `monthly_energy_charged`    | kWh     | Divide by 1000; long payload only.                                             |
| `0x14` | 2        | `u16 LE`    | `out1_power`                | W       | Also parsed in short payloads; overlaps `monthly_energy_charged`.              |
| `0x16` | 4        | `u32 LE`    | `daily_energy_discharged`   | kWh     | Divide by 100; long payload only.                                              |
| `0x1A` | 4        | `u32 LE`    | `monthly_energy_discharged` | kWh     | Divide by 100; long payload only.                                              |
| `0x1C` | 1        | `u8`        | `extern1_connected`         | boolean | Nonzero is true; overlaps `monthly_energy_discharged`.                         |
| `0x1E` | 3        | unknown     | unknown                     | —       | Unused bytes through `0x20`.                                                   |
| `0x21` | 2        | `s16 LE`    | `temp_low`                  | °C      | Divide by 10; long branch only.                                                |
| `0x23` | 2        | `s16 LE`    | `temp_high`                 | °C      | Divide by 10; long branch only.                                                |
| `0x25` | 4        | unknown     | unknown                     | —       | Unused bytes through `0x28`.                                                   |
| `0x29` | 4        | `u32 LE`    | `total_energy_charged`      | kWh     | Divide by 100; payload length at least 100.                                    |
| `0x2D` | 4        | `u32 LE`    | `total_energy_discharged`   | kWh     | Divide by 100; payload length at least 100.                                    |
| `0x31` | 25       | unknown     | unknown                     | —       | Unused bytes through `0x49`.                                                   |
| `0x4A` | 2        | `u16 LE`    | `power_rating`              | W       | Payload length at least 100.                                                   |
| `0x4C` | 24       | unknown     | unknown                     | —       | Unused bytes through `0x63` in the minimum 100-byte long payload.              |
| `0x64` | variable | unknown     | unknown                     | —       | Any remaining suffix is ignored.                                              |

# Notes

The implementation intentionally contains overlapping interpretations. This document records the code exactly and does not assert that all overlapping fields are simultaneously valid on every Venus firmware. Short-format offsets are marked tentative in the source.
