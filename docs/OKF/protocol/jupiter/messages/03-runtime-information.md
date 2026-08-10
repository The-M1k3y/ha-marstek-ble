---
type: BLE Message
title: Jupiter-C Plus 0x03 runtime summary
description: Sanitized runtime response fields for PV inputs, output, battery state, energy counters, and firmware versions.
tags: [jupiter, ble, telemetry, runtime]
status: draft
source_revision: "863e113761b0b3d589fa727728307c2c0f4d58e2"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-10T11:10:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter field map
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/863e113761b0b3d589fa727728307c2c0f4d58e2/custom_components/marstek_ble/products/jupiter.py
    title: Declarative Jupiter model
---

# Response

Payload length: 74 bytes. Offsets are relative to the payload.

| Offset | Length | Type          | Name                      | Canonical value                         | Confidence |
| -----: | -----: | ------------- | ------------------------- | --------------------------------------- | ---------- |
| `0x00` |      2 | `u16 LE`      | PV input 1 power          | W                                       | Confirmed  |
| `0x02` |      1 | `u8 / bool`   | PV input 1 connected      | boolean                                 | Confirmed  |
| `0x03` |      2 | `u16 LE`      | PV input 2 power          | W                                       | Confirmed  |
| `0x05` |      1 | `u8 / bool`   | PV input 2 connected      | boolean                                 | Confirmed  |
| `0x06` |      2 | `u16 LE`      | PV input 3 power          | W                                       | Confirmed  |
| `0x08` |      1 | `u8 / bool`   | PV input 3 connected      | boolean                                 | Confirmed  |
| `0x09` |      2 | `u16 LE`      | PV input 4 power          | W                                       | Confirmed  |
| `0x0B` |      1 | `u8 / bool`   | PV input 4 connected      | boolean                                 | Confirmed  |
| `0x0C` |      2 | `u16 LE`      | AC output power           | W                                       | Confirmed  |
| `0x0E` |      1 | `u8 / bool`   | AC output active          | boolean                                 | Confirmed  |
| `0x0F` |      3 | unknown       | unknown                   | —                                       | —          |
| `0x12` |      1 | `u8 state`    | Battery state             | 0 idle, 1 charging, 2 discharging       | Confirmed  |
| `0x13` |      2 | `u16 LE`      | Stored battery energy     | raw × 10 Wh                             | Confirmed  |
| `0x15` |      1 | `u8`          | Battery state of charge   | %                                       | Confirmed  |
| `0x16` |      1 | `u8`          | EMS firmware summary      | raw                                     | Confirmed  |
| `0x17` |      4 | `u32 LE`      | Daily PV generation       | raw ÷ 100 kWh                           | Strong     |
| `0x1B` |      4 | `u32 LE`      | Monthly PV generation     | raw ÷ 100 kWh                           | Strong     |
| `0x1F` |      4 | `u32 LE`      | Total PV generation       | raw ÷ 100 kWh                           | Confirmed  |
| `0x23` |      4 | unknown       | unknown                   | —                                       | —          |
| `0x27` |      4 | `u32 LE`      | Daily discharge energy    | raw ÷ 100 kWh                           | Confirmed  |
| `0x2B` |      4 | `u32 LE`      | Monthly discharge energy  | raw ÷ 100 kWh                           | Confirmed  |
| `0x2F` |      2 | `u16 LE`      | EMS firmware version      | raw                                     | Confirmed  |
| `0x31` |      2 | `u16 LE`      | Inverter firmware version | raw                                     | Confirmed  |
| `0x33` |      2 | `u16 LE`      | MPPT firmware version     | raw                                     | Confirmed  |
| `0x35` |      2 | `u16 LE`      | BMS firmware version      | raw                                     | Confirmed  |
| `0x37` |      5 | unknown       | unknown                   | —                                       | —          |
| `0x3C` |      1 | `u8 bitfield` | Operational status        | raw                                     | Tentative  |
| `0x3D` |     13 | unknown       | unknown                   | —                                       | —          |

The battery-state mapping is supported by controlled observations of idle,
charging, and forced discharge. Unrecognized raw values are exposed as
`unknown` rather than treated as charging.

The stored-energy, state-of-charge, generation, discharge, and firmware fields
share canonical destinations with more precise or duplicate fields in `0x14`.
The latest successfully parsed packet updates the cumulative value.
