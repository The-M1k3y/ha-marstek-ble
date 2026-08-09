---
type: Protocol Index
title: Jupiter-C Plus BLE protocol
description: Progressive entry point for sanitized Jupiter packet schemas, runtime behavior, data modeling, and battery-expansion topology.
tags: [jupiter, ble, protocol, index]
status: draft
source_revision: "382dc8ce426b44fbe59ef23ae50487e62774bcef"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-09T10:20:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter-C Plus BLE field map
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/products/jupiter.py
    title: Declarative Jupiter product model
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/products/jupiter_runtime.py
    title: Enabled Jupiter runtime
---

# Jupiter-C Plus BLE protocol

- [Message schemas](messages/) - Command-level packet documentation.
- [Battery expansions](battery-expansions.md) - Repeated records, child-device identity, setup-time discovery, and repair signaling.
- [Sanitized source map](../../../sources/jupiter-c-plus-ble-field-map.md) - Structural field map without private capture material.

Jupiter-C Plus is runtime-enabled for read-only telemetry and is discovered through the `MST_JPLS_*` advertising-name pattern. Its runtime owns its packet schemas and polling schedule; command numbers shared with Venus do not imply shared layouts or controls.

The live runtime polls `0x03` and `0x14` on the fast cadence and polls `0x0D`, `0x08`, `0x22`, `0x21`, `0x24`, `0x04`, and `0x13` on the medium cadence. It does not poll Jupiter `0x1A` or `0x1C` because the sanitized source contains no observed response structure for those commands.

The full declarative entity plan is not yet connected to Home Assistant platforms. In particular, per-PV generated entities, battery-pack child devices, and expansion repairs remain modeled but not live. Current Jupiter exposure uses safe overlapping legacy sensor fields, and Venus write/control platforms are disabled for Jupiter.
