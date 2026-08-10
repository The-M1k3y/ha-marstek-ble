---
type: BLE Message
title: Jupiter-C Plus 0x03 runtime summary
description: Sanitized runtime response fields for PV inputs, grid validity, battery state, energy counters, inverter errors, operational status, and firmware versions.
tags: [jupiter, ble, telemetry, runtime]
status: draft
source_revision: "306dce61854f5626dfb4a8454fe686791c39b2d9"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-10T18:09:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/306dce61854f5626dfb4a8454fe686791c39b2d9/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter field map
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/8614c49855e2b471cf57113d6297b8321ced9e6f/custom_components/marstek_ble/products/jupiter.py
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
| `0x0E` |      1 | `u8 / bool`   | Grid connection valid     | boolean                                 | Confirmed  |
| `0x0F` |      3 | unknown       | unknown                   | —                                       | —          |
| `0x12` |      1 | `u8 state`    | Battery state             | 0 idle, 1 charging, 2 discharging       | Confirmed  |
| `0x13` |      2 | `u16 LE`      | Stored battery energy     | raw × 10 Wh                             | Confirmed  |
| `0x15` |      1 | `u8`          | Battery state of charge   | %                                       | Confirmed  |
| `0x16` |      1 | `u8`          | EMS firmware summary      | raw                                     | Confirmed  |
| `0x17` |      4 | `u32 LE`      | Daily PV generation       | raw ÷ 100 kWh                           | Strong     |
| `0x1B` |      4 | `u32 LE`      | Monthly PV generation     | raw ÷ 100 kWh                           | Strong     |
| `0x1F` |      4 | `u32 LE`      | Total PV generation       | raw ÷ 100 kWh                           | Confirmed  |
| `0x23` |      2 | `u16 LE`      | Inverter error code       | raw                                     | Confirmed  |
| `0x25` |      2 | unknown       | unknown                   | —                                       | —          |
| `0x27` |      4 | `u32 LE`      | Daily discharge energy    | raw ÷ 100 kWh                           | Confirmed  |
| `0x2B` |      4 | `u32 LE`      | Monthly discharge energy  | raw ÷ 100 kWh                           | Confirmed  |
| `0x2F` |      2 | `u16 LE`      | EMS firmware version      | raw                                     | Confirmed  |
| `0x31` |      2 | `u16 LE`      | Inverter firmware version | raw                                     | Confirmed  |
| `0x33` |      2 | `u16 LE`      | MPPT firmware version     | raw                                     | Confirmed  |
| `0x35` |      2 | `u16 LE`      | BMS firmware version      | raw                                     | Confirmed  |
| `0x37` |      5 | unknown       | unknown                   | —                                       | —          |
| `0x3C` |      1 | `u8 bitfield` | Operational status        | raw                                     | Tentative  |
| `0x3D` |     13 | unknown       | unknown                   | —                                       | —          |

# Operational status at `0x3C`

The exact meaning of this byte is not yet understood. Observed values `0x00`,
`0x01`, and `0x03` are consistent with a bitfield, but individual bit semantics
remain provisional.

Bit 1 (`0x02`) correlates with an internal full-battery/excess-energy handling
mode. It has been observed set during the special full-battery discharge/headroom
sequence and during subsequent PV-following excess-energy export. A later
counterexample showed the same bit clear during substantial scheduled grid
export supported mainly by the battery. Bit 1 therefore does **not** simply mean
surplus feed-in, grid export, inverter active, or battery discharge, and there is
not yet enough evidence to equate it with the user-facing surplus-feed-in
configuration. `excess-energy/full-battery mode` is only a working description,
not a confirmed semantic name. Bit 0 remains unresolved.

The grid-valid flag is independent of requested/output power: it remains true at
zero target power, clears on physical AC/grid removal, and can remain false for
a period after valid grid voltage and frequency measurements return. It therefore
represents a qualified/valid grid connection rather than an active AC-output
state or raw voltage-presence indication.

The inverter-error field at `0x23` mirrors command `0x14` offset `0x02`. During a
controlled grid disconnect the observed transition was a transient `0x040A`
followed by persistent `0x0426`. The field mapping is confirmed. Based on typical
grid-tie inverter behaviour, `0x040A` is tentatively labeled **overfrequency** and
`0x0426` **island / anti-islanding detection**; those code meanings are not yet
confirmed.

The battery-state mapping is supported by controlled observations of idle,
charging, and forced discharge. Unrecognized raw values are exposed as
`unknown` rather than treated as charging.

The stored-energy, state-of-charge, generation, discharge, firmware, and inverter
error fields share canonical destinations with more precise or duplicate fields
in `0x14`. The latest successfully parsed packet updates the cumulative value.