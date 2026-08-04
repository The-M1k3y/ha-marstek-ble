---
type: BLE Message
title: Venus 0x08 Wi-Fi SSID
description: Variable-length ASCII Wi-Fi SSID response.
tags: [venus, ble, telemetry, wifi]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Wi-Fi SSID parser
---

# Request

Command `0x08` is sent with an empty payload during medium polls.

# Payload schema

| Offset | Length   | Type  | Name        | Unit | Description                                                                            |
| ------: | -------: | ----- | ----------- | ---- | -------------------------------------------------------------------------------------- |
| `0x00` | variable | ASCII | `wifi_ssid` | —    | Entire payload decoded with invalid bytes ignored; surrounding whitespace is stripped. |

There are no fixed internal field boundaries. Undecodable bytes are unused.
