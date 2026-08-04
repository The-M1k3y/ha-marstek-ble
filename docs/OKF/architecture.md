---
type: Software Architecture
title: Marstek BLE runtime architecture
description: Setup, polling, BLE lifecycle, parsing, state propagation, diagnostics, and current product-coupling points.
tags: [architecture, coordinator, polling, bluetooth, multi-product]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T09:37:02Z }
sources:
  - id: init
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/__init__.py
    title: Integration setup and unload module
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/coordinator.py
    title: Data update coordinator
  - id: device
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Protocol and BLE device implementation
  - id: sensors
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/sensor.py
    title: Sensor platform
  - id: diagnostics
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/diagnostics.py
    title: Diagnostics implementation
  - id: manifest
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/manifest.json
    title: Integration manifest
---

# Runtime data flow

```text
Home Assistant Bluetooth discovery
        │
        ▼
Config entry (`address`, advertised name, polling options)
        │
        ▼
MarstekDataUpdateCoordinator
        │ owns
        ├── MarstekBLEDevice ── write FF01 / notify FF02
        │                         │
        │                         ▼
        │                 MarstekProtocol
        │                         │ updates
        ▼                         ▼
Polling schedule ───────────► MarstekData snapshot
                                  │
                                  ▼
                       CoordinatorEntity platforms
```

During setup, Home Assistant resolves a connectable BLE device, constructs one coordinator and one persistent `MarstekBLEDevice`, starts the coordinator, waits up to 30 seconds for an advertisement, registers the device, and forwards platform setup.[^init][^coordinator]

# Poll scheduling

The coordinator has two execution triggers:

1. Home Assistant active-Bluetooth update events; and
2. a strict time-based interval fallback, so polling can continue without fresh advertisement events.

Both paths enter the same poll lock, preventing overlapping poll cycles for one coordinator.[^coordinator]

## Fast poll

At every configured fast interval, the coordinator requests:

1. runtime information (`0x03`); and
2. BMS data (`0x14`).

## Medium poll

On the first cycle and then every calculated medium cycle, it requests, in order:

1. system data (`0x0D`),
2. Wi-Fi SSID (`0x08`),
3. configuration data (`0x1A`),
4. CT polling rate (`0x22`),
5. meter IP (`0x21`) with payload `0x0B`,
6. network information (`0x24`),
7. device information (`0x04`),
8. timer information (`0x13`), and
9. logs (`0x1C`).[^coordinator]

`0x1C` is polled but has no parser dispatch in `MarstekProtocol`, so its notifications are recorded diagnostically but do not update `MarstekData`.[^coordinator][^device]

# BLE connection and command serialization

`MarstekBLEDevice` maintains a cached Bleak client, refreshes the `BLEDevice` reference through Home Assistant when reconnecting, subscribes to notifications after connecting, and schedules a disconnect after 30 seconds without a command.[^device]

An operation lock serializes complete command transactions. A transaction writes one frame, then waits for a notification carrying the same command byte. This design prevents two commands from simultaneously owning the single pending-response slot.[^device]

The declared command retry count defaults to three. Transport exceptions trigger disconnect/reconnect and another attempt; a successful write that receives no matching response within two seconds is recorded as `no_response` and currently returns `False` without advancing to another retry attempt.[^device]

# Parsing and state propagation

Notifications are validated and dispatched synchronously. A successful parser mutates the shared `MarstekData` object, records per-field source command/timestamp/payload metadata, and asks the coordinator to notify entity listeners.[^device][^coordinator]

The data object is cumulative: a command updates only fields covered by that parser, while other fields retain their previous values. This allows fast and medium data to coexist in one snapshot, but consumers must account for different ages.

Numeric and text sensors use the field-update metadata to become unavailable after ten minutes without an update. Derived sensors track all source fields they depend on. Binary sensors check coordinator availability but do not apply the same per-field ten-minute stale threshold.[^sensors]

# Failure handling

Individual poll commands use a best-effort wrapper: a failure is logged and later commands in the same poll still execute. After a cycle, any failed command raises a module-global backoff level. The configured levels are `1, 5, 15, 30, 60 s`; because the state is module-global, a failure from one configured unit pauses polling for all coordinator instances in the Home Assistant process.[^coordinator]

A fully successful cycle clears the global backoff.

# Diagnostics

The BLE device retains the latest 25 command results and 25 notifications, per-command counters, response ratios, timestamps, payload/frame hex, and last errors. Home Assistant diagnostics add coordinator intervals/counters and the full data snapshot, then redact Wi-Fi, network, meter, MAC, and device identifiers.[^device][^diagnostics]

# Current product-coupling points

The current implementation is Venus-specific in several places:

- discovery prefixes are a single global tuple;
- setup and every entity platform hard-code model `Venus E`;
- one `MarstekProtocol` dispatch table and one `MarstekData` schema serve every configured unit;
- the coordinator selects one fixed set of polling commands;
- response offsets are selected only by command and, for runtime data, payload length; and
- entity creation assumes 16 battery cells.[^manifest][^init][^coordinator][^device][^sensors]

For multi-product work, product detection, command schedules, parsers, capabilities, cell count, and Home Assistant model metadata should be explicit product-profile concerns. Do not generalize a Venus offset or command meaning to another product merely because a frame has the same command byte. Product-specific concepts should remain separate until repository evidence establishes shared behavior.

[^init]: Integration setup and unload module.
[^coordinator]: Data update coordinator.
[^device]: Protocol and BLE device implementation.
[^sensors]: Sensor platform.
[^diagnostics]: Diagnostics implementation.
[^manifest]: Integration manifest.
