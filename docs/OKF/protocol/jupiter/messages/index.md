---
type: Protocol Index
title: Jupiter-C Plus BLE messages
description: Index of sanitized Jupiter telemetry and status response schemas.
tags: [jupiter, ble, messages, index]
status: draft
source_revision: "17d3211e12989eb428681f5959707e9403e61bf6"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-05T14:19:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter-C Plus BLE field map
---

# Jupiter-C Plus BLE messages

- [`0x03` runtime summary](03-runtime-information.md) - PV presence and power, output state, battery state, energy counters, and firmware versions.
- [`0x13` event history](13-event-history.md) - Twenty fixed records with timestamp components and unresolved event bytes.
- [`0x14` detailed telemetry](14-detailed-telemetry.md) - Inverter, grid, MPPT, PV input, battery, and expansion-pack fields.
- [Other responses](other-responses.md) - Identity, SSID, unresolved status responses, and commands without a response schema.
