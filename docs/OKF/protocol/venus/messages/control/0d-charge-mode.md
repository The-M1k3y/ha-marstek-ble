---
type: BLE Message
title: Venus 0x0D charge mode
description: Charge-mode selector write sharing command 0x0D with system-data reads.
tags: [venus, ble, control, configuration, dual-use]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: select
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/select.py
    title: Charge-mode selector
---

# Request schema

Command byte: `0x0D`. An empty request instead queries [system data](../telemetry/0d-system-data.md).

| Offset | Length | Type | Name          | Unit | Description                                                                                  |
| ------: | -----: | ---- | ------------- | ---- | -------------------------------------------------------------------------------------------- |
| `0x00` | 1      | `u8` | `charge_mode` | —    | `0` = PV2 Passthrough, `1` = Load First, `2` = Simultaneous Charge Discharge.                |

No additional request bytes are used. Readback comes from `config_mode` in command `0x1A`, not from a parsed write response.
