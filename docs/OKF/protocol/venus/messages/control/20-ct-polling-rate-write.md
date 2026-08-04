---
type: BLE Message
title: Venus 0x20 CT polling-rate write
description: CT polling-rate selector write message.
tags: [venus, ble, control, ct]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: select
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/select.py
    title: CT polling-rate selector
---

# Request schema

Command byte: `0x20`.

| Offset | Length | Type | Name              | Unit | Description                                      |
| ------: | -----: | ---- | ----------------- | ---- | ------------------------------------------------ |
| `0x00` | 1      | `u8` | `ct_polling_rate` | —    | `0` = Fastest, `1` = Medium, `2` = Slowest.     |

No additional request bytes are used. Readback is provided by command [`0x22`](../telemetry/22-ct-polling-rate.md).
