---
type: Software Architecture
title: Marstek BLE runtime architecture
description: Product selection, polling, BLE lifecycle, product-specific parsing, declarative entities, and capability boundaries.
tags: [architecture, coordinator, polling, bluetooth, multi-product]
status: draft
source_revision: "aaab90ae2bde49671ee9081fb0df499ff1134134"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-13T12:00:00Z }
sources:
  - id: init
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/__init__.py
    title: Integration setup and platform capabilities
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/product_coordinator.py
    title: Product-aware coordinator
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/product_runtime.py
    title: Product runtime and protocol dispatcher
  - id: entities
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/product_entity_platform.py
    title: Live declarative entity synchronization
  - id: jupiter-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/products/jupiter_runtime.py
    title: Jupiter runtime
---

# Runtime data flow

```text
Bluetooth discovery
  -> config entry + product_id
  -> ProductRuntime registry
  -> ProductDataUpdateCoordinator
       -> MarstekBLEDevice transport
       -> ProductProtocol frame validation
       -> product-specific parser/poll schedule
  -> product-specific cumulative data
  -> ProductProfile entity plan
  -> sensor / binary_sensor entities
```

Venus and Jupiter-C Plus are explicitly registered runtime products. New entries persist a product ID; legacy entries without one retain the Venus fallback. Unknown persisted product IDs are rejected.

# Polling

Venus keeps its product-specific schedule. Jupiter uses only response structures retained in the sanitized Jupiter source.

| Cadence | Jupiter commands |
| ------- | ---------------- |
| Fast    | `0x03`, `0x14`   |
| Medium  | `0x0D`, `0x08`, `0x04`, `0x13` |

Jupiter does not poll `0x1A`, `0x1C`, `0x21`, `0x22`, or `0x24`, because their Jupiter semantics are absent or unresolved. Product profiles declare the commands that may be placed in their polling schedules. Runtime construction rejects an unsupported scheduled command; model identification (`0x04`) is the sole exception.

# Parsing and state

`ProductProtocol` validates the common frame structure and dispatches the payload only to the selected runtime. Fixed binary packets use declarative field metadata. Irregular text packets remain product-local custom parsers.

Venus stores nested `VenusData`; Jupiter stores `RuntimeJupiterData`. Jupiter additionally parses comma-separated `0x04` identity/version data and variable-length `0x08` Wi-Fi SSID data. Compatibility aliases remain available for regression/transition code, but live sensor creation now reads canonical `ProductProfile` bindings.

# Entity and device creation

`sensor.py` and `binary_sensor.py` consume `ProductProfile.build_entity_plan()`. Fixed entities are created immediately. Repeated Jupiter battery-pack entities are created when the reported pack count makes the corresponding slot present.

A `ProductEntityManager` listens for later coordinator updates. If the pack count increases, only the newly available child bindings are added. Existing child bindings are never renumbered. If the count decreases, their presence condition makes the removed slot unavailable without shifting identities.

Jupiter battery child identifiers are positional and stable:

```text
<main BLE identifier>:battery_pack:0
<main BLE identifier>:battery_pack:1
<main BLE identifier>:battery_pack:2
<main BLE identifier>:battery_pack:3
```

This exposes the modeled per-PV entities and populated base/expansion battery entities through Home Assistant.

# Capability boundary

Venus loads sensor, binary-sensor, button, switch, and select platforms. Jupiter loads only sensor and binary-sensor platforms. Venus write/control command semantics are not assumed to apply to Jupiter.

The remaining multi-product migration work is primarily on write/control capabilities and optional repair UX; the declarative read-only entity layer is live.
