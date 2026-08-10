---
type: Protocol Index
title: Jupiter-C Plus BLE messages
description: Index of sanitized Jupiter telemetry, event, and status response schemas.
tags: [jupiter, ble, messages, index]
status: draft
source_revision: "8614c49855e2b471cf57113d6297b8321ced9e6f"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-10T16:16:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/6b476c58e4797c9c315a6a7c50da711b4aecf2b6/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter-C Plus BLE field map
---

# Jupiter-C Plus BLE messages

- [`0x03` runtime summary](03-runtime-information.md) - PV presence and power, grid validity, battery state, inverter errors, energy counters, and firmware versions.
- [`0x13` event history](13-event-history.md) - Twenty fixed records with timestamp components and a 16-bit event/error identifier.
- [`0x14` detailed telemetry](14-detailed-telemetry.md) - Inverter, grid, MPPT, PV input, battery, and expansion-pack fields.
- [Other responses](other-responses.md) - Identity, SSID, unresolved status responses, and commands without a response schema.
