---
type: BLE Message
title: Jupiter-C Plus 0x14 detailed telemetry
description: Inverter, grid, MPPT, PV-input, battery, and repeated battery-pack response layout.
tags: [jupiter, ble, telemetry, inverter, mppt, bms]
status: draft
source_revision: "991f4fed7522c1552b53c442a14ecf2a5aee40db"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-10T18:27:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/991f4fed7522c1552b53c442a14ecf2a5aee40db/docs/sources/jupiter-c-plus-ble-field-map.md
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

# MPPT state flags

The 16-bit state word at `0x20` is preserved in full as `MPPT State Flags`. Only
bits with repeated behavioral correlations have assigned meanings.

| Bit | Mask     | Working interpretation              | Confidence |
| --: | -------- | ----------------------------------- | ---------- |
|   0 | `0x0001` | MPPT stopped / parked / disabled    | Tentative  |
|   1 | `0x0002` | unresolved                          | —          |
|   2 | `0x0004` | MPPT controller initialized / ready | Strong     |
|   3 | `0x0008` | unresolved                          | —          |
|   4 | `0x0010` | PV input 1 active                   | Confirmed  |
|   5 | `0x0020` | PV input 2 active                   | Confirmed  |
|   6 | `0x0040` | PV input 3 active                   | Confirmed  |
|   7 | `0x0080` | PV input 4 active                   | Confirmed  |
| 8–15| `0x0100`–`0x8000` | unresolved               | —          |

The forced-full-battery captures provide a useful state-machine sequence. Normal
operation with all four PV inputs active used `0x00F4`, which is bit 2 plus bits
4–7. During the deliberate MPPT/PV shutdown associated with the battery-headroom
sequence, the state changed to `0x0001`: bit 0 was the only set bit, while the
controller-ready and all PV-active bits were clear. During restart, `0x0014`
showed bit 2 plus PV input 1 active before the remaining PV-active bits returned.
A separate `0x0004` state showed bit 2 set with no PV input active.

This strongly supports bit 2 as a controller-ready/initialized state that is
independent of whether any PV channel is currently active. Bit 0 appears to
represent an opposing stopped/parked controller state. Its exact firmware meaning
is not yet established, so **MPPT stopped / parked / disabled** remains a working
interpretation rather than a canonical semantic name. Bit 0 and bit 2 were not
observed set simultaneously in the inspected captures. Bits 1, 3, and 8–15 remain
unresolved.

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