---
type: BLE Message
title: Venus 0x1C logs
description: Log message requested by the coordinator but not parsed by the integration.
tags: [venus, ble, telemetry, logs, unknown]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/coordinator.py
    title: Log polling
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Notification dispatch
---

# Request

Command `0x1C` is sent with an empty payload during medium polls.

# Payload schema

No parser is registered for command `0x1C`.

| Offset | Length   | Type    | Name    | Unit | Description                                                                  |
| ------: | -------: | ------- | ------- | ---- | ---------------------------------------------------------------------------- |
| `0x00` | variable | unknown | unknown | —    | Entire response payload; recorded in diagnostics but otherwise unused.       |
