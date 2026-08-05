---
type: Protocol Index
title: Jupiter-C Plus BLE protocol
description: Progressive entry point for sanitized Jupiter packet schemas, data modeling, and battery-expansion topology.
tags: [jupiter, ble, protocol, index]
status: draft
source_revision: "17d3211e12989eb428681f5959707e9403e61bf6"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-05T14:19:00Z }
sources:
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter-C Plus BLE field map
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/products/jupiter.py
    title: Declarative Jupiter product model
---

# Jupiter-C Plus BLE protocol

- [Message schemas](messages/) - Command-level packet documentation.
- [Battery expansions](battery-expansions.md) - Repeated records, child-device identity, setup-time discovery, and repair signaling.
- [Sanitized source map](../../../sources/jupiter-c-plus-ble-field-map.md) - Structural field map without private capture material.

The Jupiter model is branch-only scaffolding and is not connected to the existing
integration. Command numbers shared with Venus do not imply shared layouts.
