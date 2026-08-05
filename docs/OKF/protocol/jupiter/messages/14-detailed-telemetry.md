---
type: BLE Message
title: Jupiter-C Plus 0x14 detailed telemetry
description: Inverter, grid, MPPT, PV-input, battery, and repeated battery-pack response layout.
tags: [jupiter, ble, telemetry, inverter, mppt, bms]
status: draft
source_revision: "17d3211e12989eb428681f5959707e9403e61bf6"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-05T14:19:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter field map
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/products/jupiter.py
    title: Declarative Jupiter model
---

# Response

Payload length: 166 bytes. Offsets are relative to the payload. The complete,
offset-ordered structural table is maintained in the [sanitized source
map](../../../../sources/jupiter-c-plus-ble-field-map.md). This concept groups
that structure by contiguous byte range without changing field order.

| Range         | Structure                                      |
| ------------- | ---------------------------------------------- |
| `0x00–0x1F`   | Inverter state, errors, grid values, output, temperature, and discharge counters |
| `0x20–0x27`   | MPPT state, errors, temperature, and warnings  |
| `0x28–0x3F`   | Four PV inputs, each voltage/current/power     |
| `0x40–0x4F`   | PV generation counters and one unknown range  |
| `0x50–0x57`   | MPPT DC output plus tentative base/PE voltages |
| `0x58–0x79`   | Battery limits, state, capacity, electrical values, diagnostics, pack count, and stored energy |
| `0x7A–0x99`   | Four repeated 8-byte battery-pack summaries   |
| `0x9A–0xA5`   | Battery, environment, and MOSFET temperatures |

# Multiple packet sources

Several canonical fields are also present in runtime command `0x03`, sometimes
with a different raw unit or precision. Each destination field declares one
`FieldSource` per packet and normalizes both representations before assignment.
Values absent from the selected packet remain unchanged.

# PV inputs

The four detailed PV records begin at `0x28`, have a stride of 6 bytes, and each
contain:

| Relative offset | Length | Type     | Field   | Conversion |
| --------------: | -----: | -------- | ------- | ---------- |
|         `+0x00` |      2 | `u16 LE` | Voltage | ÷ 10 V     |
|         `+0x02` |      2 | `u16 LE` | Current | ÷ 10 A     |
|         `+0x04` |      2 | `u16 LE` | Power   | ÷ 10 W     |

# Battery-pack records

The four 8-byte records start at `0x7A`. Record 0 represents the base battery;
records 1–3 represent expansion positions. The populated-record count at `0x76`
controls setup-time child-device creation.

| Relative offset | Length | Type     | Field                      | Conversion |
| --------------: | -----: | -------- | -------------------------- | ---------- |
|         `+0x00` |      1 | `u8`     | Highest-voltage cell index | raw        |
|         `+0x01` |      1 | `u8`     | Lowest-voltage cell index  | raw        |
|         `+0x02` |      2 | `u16 LE` | Highest cell voltage       | ÷ 1000 V   |
|         `+0x04` |      2 | `u16 LE` | Lowest cell voltage        | ÷ 1000 V   |
|         `+0x06` |      2 | `u16 LE` | Status or fault word       | raw        |

Status-word semantics remain tentative. See [battery
expansions](../battery-expansions.md) for child-device behavior.
