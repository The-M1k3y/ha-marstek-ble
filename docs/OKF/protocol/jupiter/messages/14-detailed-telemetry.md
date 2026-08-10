---
type: BLE Message
title: Jupiter-C Plus 0x14 detailed telemetry
description: Inverter, grid, MPPT, PV-input, battery, and repeated battery-pack response layout.
tags: [jupiter, ble, telemetry, inverter, mppt, bms]
status: draft
source_revision: "8614c49855e2b471cf57113d6297b8321ced9e6f"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-10T16:16:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/6b476c58e4797c9c315a6a7c50da711b4aecf2b6/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter field map
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/8614c49855e2b471cf57113d6297b8321ced9e6f/custom_components/marstek_ble/products/jupiter.py
    title: Declarative Jupiter model
---

# Response

Payload length: 166 bytes. Offsets are relative to the payload. The complete,
offset-ordered structural table is maintained in the [sanitized source
map](../../../../sources/jupiter-c-plus-ble-field-map.md). This concept groups
that structure by contiguous byte range without changing field order.

| Range       | Structure                                                               |
| ----------- | ----------------------------------------------------------------------- |
| `0x00–0x1F` | Inverter state, errors, grid values, output, temperature, and discharge counters |
| `0x20–0x27` | MPPT state, errors, temperature, and warnings                           |
| `0x28–0x3F` | Four PV inputs, each voltage/current/power                              |
| `0x40–0x4F` | PV generation counters and one unknown range                           |
| `0x50–0x57` | MPPT DC output plus tentative base/PE voltages                          |
| `0x58–0x79` | Battery limits, state, capacity, electrical values, diagnostics, pack count, and stored energy |
| `0x7A–0x99` | Four repeated 8-byte battery-pack summaries                            |
| `0x9A–0xA5` | Battery, environment, and MOSFET temperatures                          |

# Inverter state and grid qualification

The operating-state word at `0x00` is not an output-power flag. In a controlled
AC/grid disconnect it changed from the normal non-zero state to zero. After AC
was restored, valid grid voltage and frequency measurements returned while the
state word remained zero for a period. The individual bits are still unresolved,
but the word clearly includes inverter/grid qualification state rather than mere
voltage presence or non-zero power production.

Runtime command `0x03` offset `0x0E` exposes the related boolean **Grid Connection
Valid** state. It remains true at a zero-watt target, clears on physical grid
removal, and can remain false after voltage/frequency measurements reappear.

# Inverter errors

The inverter error code at `0x02` is mirrored by command `0x03` offset `0x23`.
During controlled grid loss it transitioned through `0x040A` before settling at
`0x0426`; the persistent value was also written as the 16-bit ID in command
`0x13` event history.

The numeric mappings are confirmed. Based on general grid-tie inverter behaviour,
`0x040A` is tentatively associated with **overfrequency** and `0x0426` with
**island / anti-islanding detection**. Those semantic labels remain tentative.

# Inverter field at `0x08`

The two-byte field at `0x08` was previously interpreted as grid current.
Controlled Jupiter observations showed it remaining zero while grid voltage and
AC output power were non-zero. Its semantics and scale are therefore unresolved.
The integration retains the field internally for future investigation but no
longer exposes it as a Home Assistant `Grid Current` sensor.

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
