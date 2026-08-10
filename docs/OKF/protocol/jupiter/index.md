---
type: Protocol Index
title: Jupiter-C Plus BLE protocol
description: Progressive entry point for sanitized Jupiter packet schemas, runtime behavior, live entities, and battery-expansion topology.
tags: [jupiter, ble, protocol, index]
status: draft
source_revision: "112abd322722b2e84bcdf34ee4b0325bf14b7313"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-09T10:50:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter-C Plus BLE field map
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/products/jupiter.py
    title: Jupiter product model
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/products/jupiter_runtime.py
    title: Jupiter runtime
---

# Jupiter-C Plus BLE protocol

- [Message schemas](messages/) - Command-level packet documentation.
- [Battery expansions](battery-expansions.md) - Repeated records, stable child-device identity, live addition, and runtime presence.
- [Sanitized source map](../../../sources/jupiter-c-plus-ble-field-map.md) - Structural field map without private capture material.

Jupiter-C Plus is runtime-enabled for read-only telemetry and discovered through `MST_JPLS_*`. Its runtime owns its packet schemas and polling schedule; shared command numbers do not imply Venus layouts or control semantics.

The runtime polls `0x03` and `0x14` on the fast cadence and `0x0D`, `0x08`, `0x22`, `0x21`, `0x24`, `0x04`, and `0x13` on the medium cadence. Jupiter `0x1A` and `0x1C` remain unpolled because no response structure is retained in the sanitized source.

The declarative sensor and binary-sensor entity plan is live. This includes the four PV inputs and child devices for populated battery-pack positions. Newly reported battery positions are added without renumbering existing children; disappearing positions become unavailable. Venus write/control platforms remain disabled for Jupiter.
