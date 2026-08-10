---
type: BLE Message
title: Jupiter-C Plus 0x13 event history
description: Twenty fixed circular-history records with timestamp components and a 16-bit event/error identifier.
tags: [jupiter, ble, event-history]
status: draft
source_revision: "8614c49855e2b471cf57113d6297b8321ced9e6f"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-10T16:16:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/6b476c58e4797c9c315a6a7c50da711b4aecf2b6/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter field map
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/8614c49855e2b471cf57113d6297b8321ced9e6f/custom_components/marstek_ble/products/jupiter.py
    title: Declarative Jupiter event records
---

# Response

Payload length: 160 bytes, exactly 20 records × 8 bytes.

| Relative offset | Length | Type     | Field          | Confidence |
| --------------: | -----: | -------- | -------------- | ---------- |
|         `+0x00` |      2 | `u16 LE` | Year           | Strong     |
|         `+0x02` |      1 | `u8`     | Month          | Strong     |
|         `+0x03` |      1 | `u8`     | Day            | Strong     |
|         `+0x04` |      1 | `u8`     | Hour           | Strong     |
|         `+0x05` |      1 | `u8`     | Minute         | Strong     |
|         `+0x06` |      2 | `u16 LE` | Event/error ID | Confirmed  |

The physical records form a circular buffer, so list order is not guaranteed to
be chronological.

A controlled AC/grid disconnect produced a persistent inverter error whose raw
16-bit value appeared unchanged in the final two bytes of a newly inserted event
record. This establishes that bytes `+0x06` and `+0x07` form one little-endian
`u16` event/error identifier rather than independent event-value and state bytes.

The integration keeps the historical byte-wise `event_value` and `event_state`
views temporarily for compatibility, but `event_code` is the canonical field.
No Home Assistant event or sensor entity is created from event history yet.
