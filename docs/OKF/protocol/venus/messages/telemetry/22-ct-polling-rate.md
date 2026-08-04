---
type: BLE Message
title: Venus 0x22 CT polling rate
description: CT polling-rate readback response.
tags: [venus, ble, telemetry, ct]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: CT polling-rate parser
---

# Request

Command `0x22` is sent with an empty payload during medium polls.

Minimum response payload length: 1 byte.

# Payload schema

| Offset | Length   | Type    | Name              | Unit | Description                                                        |
| ------: | -------: | ------- | ----------------- | ---- | ------------------------------------------------------------------ |
| `0x00` | 1        | `u8`    | `ct_polling_rate` | —    | `0` = Fastest, `1` = Medium, `2` = Slowest in the select mapping. |
| `0x01` | variable | unknown | unknown           | —    | Any remaining suffix is ignored.                                  |
