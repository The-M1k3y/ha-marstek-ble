---
type: Protocol Reference
title: Venus BLE transport and framing
description: GATT transport, frame encoding, checksum validation, command correlation, and connection behavior implemented for Venus units.
tags: [venus, ble, gatt, protocol, framing]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T09:37:02Z }
sources:
  - id: constants
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/const.py
    title: BLE UUID and frame constants
  - id: device
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Protocol and BLE device implementation
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/coordinator.py
    title: Coordinator notification and polling behavior
  - id: manifest
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/manifest.json
    title: Bluetooth discovery manifest
---

# Scope

This document describes the Venus BLE protocol exactly as encoded and decoded by the repository. It is an implementation reference, not a vendor protocol specification. See [the knowledge scope](scope.md) before extending it to another product.

# Discovery and GATT characteristics

The integration discovers connectable devices using the Venus advertising-name patterns in the manifest.[^manifest]

| Role | UUID |
|---|---|
| Service | `0000ff00-0000-1000-8000-00805f9b34fb` |
| Command write | `0000ff01-0000-1000-8000-00805f9b34fb` |
| Notification receive | `0000ff02-0000-1000-8000-00805f9b34fb` |

Commands are written to `FF01`. Responses and other device frames arrive as notifications on `FF02`.[^constants][^device]

# Frame schema

Both outgoing commands and parsed notifications use this byte layout:

| Offset | Size | Meaning |
|---:|---:|---|
| `0` | 1 | Start byte `0x73` |
| `1` | 1 | Total frame length, including checksum |
| `2` | 1 | Frame type `0x23` |
| `3` | 1 | Command identifier |
| `4` | variable | Command or response payload |
| final | 1 | XOR checksum |

In symbolic form:

```text
73 LL 23 CC [payload ...] XX
```

The builder initially creates `[0x73, 0x00, 0x23, command]`, appends the payload, stores `len(frame) + 1` in `LL`, XORs every byte accumulated so far, and appends that XOR as `XX`. Therefore `LL` equals the final number of bytes in the frame.[^device]

## Checksum

```python
checksum = 0
for byte in frame_without_checksum:
    checksum ^= byte
```

The notification parser recomputes the XOR over all bytes except the final byte and rejects a mismatch.[^device]

# Notification validation

A notification is accepted for parsing only when:

- it contains at least five bytes;
- byte `0` is `0x73`;
- byte `2` is `0x23`; and
- the final byte equals the XOR checksum.

The current parser does **not** independently compare the length byte with the actual received length. After validation, byte `3` selects the parser and bytes `4:-1` are the payload.[^device]

# Request and response behavior

The implementation supports one in-flight command per `MarstekBLEDevice`:

1. acquire the operation lock;
2. ensure a BLE connection and notification subscription;
3. set the pending command byte and a new response event;
4. write the frame to `FF01`;
5. wait up to `2.0 s`; and
6. treat a notification with the same byte at offset `3` as the response.

There is no transaction identifier. Correlation is based only on the command byte, which is safe within the implementation because command operations are serialized.[^device]

The matching notification is signalled whether or not its payload parser recognizes the command. Parsing success controls Home Assistant data updates, while command completion only requires the matching command byte.[^device][^coordinator]

# Connection lifecycle

The BLE client is established through `bleak_retry_connector` using the service cache. Notifications are started once per connection. A fresh Home Assistant `BLEDevice` reference may be obtained before reconnecting, which supports direct adapters and BLE proxies.[^device]

After every transmitted command, the integration resets an inactivity timer. If no further command is sent for 30 seconds, the client disconnects intentionally. A later command reconnects as needed.[^device]

# Parser dispatch

The notification command byte currently routes to these payload parsers:

| Command | Parser |
|---:|---|
| `0x03` | Runtime information |
| `0x04` | Device information |
| `0x08` | Wi-Fi SSID |
| `0x0D` | System data |
| `0x13` | Timer information |
| `0x14` | BMS data |
| `0x1A` | Configuration data |
| `0x21` | Meter IP |
| `0x22` | CT polling rate |
| `0x24` | Network information |
| `0x28` | Local API status |

Other command notifications are recorded in diagnostics and return `False` from `parse_notification`.[^device]

# Byte order

All binary multi-byte fields parsed by the repository use little-endian `struct` formats (`<H`, `<h`, `<I`). ASCII-based responses are decoded separately. The exact field layouts and scaling are listed in [Venus command and payload reference](venus-command-reference.md).

[^constants]: BLE UUID and frame constants.
[^device]: Protocol and BLE device implementation.
[^coordinator]: Coordinator notification and polling behavior.
[^manifest]: Bluetooth discovery manifest.
