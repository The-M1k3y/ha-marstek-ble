---
type: BLE Message
title: Jupiter-C Plus 0x13 event history
description: Twenty fixed circular-history records with timestamp components and unresolved event bytes.
tags: [jupiter, ble, event-history]
status: draft
source_revision: "75cf9f3750cffe4c7c344458a443885b0bf4248c"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-10T12:16:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter field map
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/75cf9f3750cffe4c7c344458a443885b0bf4248c/custom_components/marstek_ble/products/jupiter.py
    title: Declarative Jupiter event records
---

# Response

Payload length: 160 bytes, exactly 20 records × 8 bytes.

| Relative offset | Length | Type     | Field               | Confidence |
| --------------: | -----: | -------- | ------------------- | ---------- |
|         `+0x00` |      2 | `u16 LE` | Year                | Strong     |
|         `+0x02` |      1 | `u8`     | Month               | Strong     |
|         `+0x03` |      1 | `u8`     | Day                 | Strong     |
|         `+0x04` |      1 | `u8`     | Hour                | Strong     |
|         `+0x05` |      1 | `u8`     | Minute              | Strong     |
|         `+0x06` |      1 | `u8`     | Event value or ID   | Tentative  |
|         `+0x07` |      1 | `u8`     | Event type or state | Tentative  |

The physical records form a circular buffer, so list order is not guaranteed to
be chronological. Event-byte semantics remain unresolved.

Each physical record slot is exposed as one diagnostic text sensor named
`Event N Record`. Its value combines the timestamp fields with the two unresolved
bytes in hexadecimal form:

```text
2026-08-10 14:05 | 0x12 0xA4
```

The timestamp and raw bytes remain separately parsed in the in-memory record for
protocol analysis, but they do not create separate Home Assistant entities. This
keeps the diagnostic surface compact while preserving the fixed physical slot
order and the exact unresolved byte values for long-running observation and
correlation.
