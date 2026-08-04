---
type: BLE Message
title: Venus 0x28 local API status
description: Local API status response accepted by the parser.
tags: [venus, ble, telemetry, local-api]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Local API status parser
---

# Request status

The parser accepts command `0x28`, but the current coordinator does not poll it.

Minimum response payload length: 3 bytes.

# Payload schema

| Offset | Length   | Type     | Name                | Unit     | Description                                                          |
| ------: | -------: | -------- | ------------------- | -------- | -------------------------------------------------------------------- |
| `0x00` | 1        | `u8`     | `local_api_enabled` | boolean  | Exactly 1 means enabled; every other value means disabled.           |
| `0x01` | 2        | `u16 LE` | `local_api_port`    | TCP port | Combined into `enabled/<port>` or `disabled/<port>`.                 |
| `0x03` | variable | unknown  | unknown             | —        | Any remaining suffix is ignored.                                    |
