---
type: BLE Message
title: Venus 0x25 reboot
description: Empty-payload device reboot request.
tags: [venus, ble, control, reboot]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: button
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/button.py
    title: Reboot button
---

# Request schema

Command byte: `0x25`.

| Offset | Length | Type  | Name     | Unit | Description                       |
| ------: | -----: | ----- | -------- | ---- | --------------------------------- |
| —      | 0      | empty | `reboot` | —    | The request has no payload bytes. |

No command-specific response payload is parsed.
