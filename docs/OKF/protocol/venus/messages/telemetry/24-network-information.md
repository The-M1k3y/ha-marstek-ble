---
type: BLE Message
title: Venus 0x24 network information
description: Variable-length ASCII network configuration response.
tags: [venus, ble, telemetry, network]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
sources:
  - id: parser
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Network-information parser
---

# Request

Command `0x24` is sent with an empty payload during medium polls.

# Payload schema

| Offset | Length   | Type      | Name           | Unit | Description                                                          |
| ------: | -------: | --------- | -------------- | ---- | -------------------------------------------------------------------- |
| `0x00` | variable | ASCII CSV | `network_info` | —    | Entire payload retained and parsed as comma-separated `key:value`.   |

Byte offsets inside the payload are variable.

# Recognized fields

| Key               | Name          | Description                 |
| ----------------- | ------------- | --------------------------- |
| `ip`              | `ip_address`  | Device IPv4 address string. |
| `gate`, `gateway` | `gateway`     | Gateway address string.     |
| `mask`            | `subnet_mask` | Subnet-mask string.         |
| `dns`             | `dns_server`  | DNS-server address string.  |

Unknown keys, entries without `:`, and undecodable bytes are ignored.
