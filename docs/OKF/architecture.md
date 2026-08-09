---
type: Software Architecture
title: Marstek BLE runtime architecture
description: Product selection, polling, BLE lifecycle, product-specific parsing, state propagation, diagnostics, and remaining migration boundaries.
tags: [architecture, coordinator, polling, bluetooth, multi-product]
status: draft
source_revision: "382dc8ce426b44fbe59ef23ae50487e62774bcef"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-09T10:20:00Z }
sources:
  - id: init
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/__init__.py
    title: Integration setup and product/platform selection
  - id: config-flow
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/config_flow.py
    title: Discovery and persisted product selection
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/product_coordinator.py
    title: Product-aware coordinator adapter
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/product_runtime.py
    title: Generic product runtime and frame parser
  - id: venus-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/products/venus_runtime.py
    title: Venus parsing and polling runtime
  - id: jupiter-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/products/jupiter_runtime.py
    title: Jupiter parsing, polling, and compatibility runtime
  - id: device
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/marstek_device.py
    title: Shared BLE transport and legacy Venus parser
---

# Runtime data flow

```text
Home Assistant Bluetooth discovery
        │
        ▼
Config entry (`address`, name, `product_id`, polling options)
        │
        ▼
Enabled ProductRuntime registry
        │
        ▼
ProductDataUpdateCoordinator
        │ owns
        ├── MarstekBLEDevice ── shared BLE transport
        │
        ├── ProductProtocol ─── frame validation and runtime dispatch
        │
        └── ProductRuntime ──── packet schemas + poll schedule
                                  │
                                  ▼
                         product-specific data
                   (`VenusData` / `RuntimeJupiterData`)
                                  │
                                  ▼
                       CoordinatorEntity platforms
```

The live integration selects an explicit product runtime. New config entries persist the selected `product_id`; entries created before this migration have no product ID and retain a Venus fallback for compatibility. A persisted unknown product ID is rejected instead of being interpreted as Venus.[^init][^config-flow]

The enabled registry contains Venus and Jupiter-C Plus. Their discovery prefixes, packet schemas, custom parsers, and poll schedules remain product-owned rather than inferred from shared command numbers.

# Coordinator and BLE transport boundary

`ProductDataUpdateCoordinator` subclasses the existing coordinator to reuse scheduling, backoff, polling locks, availability handling, and the persistent `MarstekBLEDevice`. It replaces only the product-dependent pieces:

- cumulative data object;
- notification protocol/parser; and
- fast and medium command schedules.[^coordinator]

`MarstekBLEDevice` remains the shared transport. It owns connection establishment, notification subscription, command serialization, response waiting, retry behavior, diagnostics history, and disconnect handling.[^device]

The old flat `MarstekData` and `MarstekProtocol` remain in `marstek_device.py` for compatibility and regression coverage, but config-entry setup no longer uses them as the live coordinator state/parser.

# Venus polling

The Venus runtime preserves the existing product schedule.[^venus-runtime]

## Fast poll

1. runtime information (`0x03`), delay `0.1 s`;
2. BMS data (`0x14`), delay `0.1 s`.

## Medium poll

On the first cycle and then every calculated medium cycle:

1. system data (`0x0D`),
2. Wi-Fi SSID (`0x08`),
3. configuration data (`0x1A`),
4. CT polling rate (`0x22`),
5. meter IP (`0x21`) with payload `0x0B`,
6. network information (`0x24`),
7. device information (`0x04`),
8. timer information (`0x13`),
9. local API status (`0x28`), and
10. logs (`0x1C`).

# Jupiter polling

The Jupiter runtime uses only response structures retained by the sanitized Jupiter source.[^jupiter-runtime]

## Fast poll

1. runtime summary (`0x03`), delay `0.1 s`;
2. detailed inverter/MPPT/BMS telemetry (`0x14`), delay `0.1 s`.

## Medium poll

1. unresolved 12-byte status (`0x0D`),
2. Wi-Fi SSID (`0x08`),
3. raw status (`0x22`),
4. raw status (`0x21`) with payload `0x0B`,
5. raw status (`0x24`),
6. device information (`0x04`), and
7. 20-record event history (`0x13`).

Jupiter does not poll `0x1A` or `0x1C`; the sanitized field map records no observed response structure for those commands. This is an explicit product difference from Venus, not a transport-level omission.

# Product-specific parsing and state

`ProductProtocol` performs common Marstek frame validation: minimum frame size, start/type bytes, declared frame length, and XOR checksum. It then dispatches the payload to the selected `ProductRuntime`.[^runtime]

Fixed binary packets use declarative `PacketSchema` / `FieldSource` traversal. Text-like packets that need key/value or string parsing remain product-specific payload functions.

Venus stores canonical state in nested `VenusData`. Jupiter stores canonical state in `RuntimeJupiterData`, which extends the declarative Jupiter model with field-update tracking and temporary flat aliases required by the current sensor modules. Jupiter aliases are limited to fields with a defensible semantic equivalent; unsupported Venus-only fields remain `None` rather than receiving guessed meanings.[^venus-runtime][^jupiter-runtime]

# Product selection and platform capability boundary

Discovery maps an advertised local name to an enabled runtime and persists its stable product ID. The manifest and discovery prefix set include `MST_JPLS_*` for Jupiter-C Plus.

Venus currently loads sensor, binary-sensor, button, switch, and select platforms. Jupiter loads only sensor and binary-sensor platforms. Its write/control command semantics have not been validated and therefore Venus button/switch/select implementations are deliberately not exposed for Jupiter.[^init]

# Remaining migration boundaries

The declarative entity-plan generator is still not connected to the Home Assistant platform modules. Consequently:

- the current Jupiter runtime exposes safe overlapping telemetry through a compatibility layer rather than the full declarative entity set;
- per-PV entities described by the Jupiter profile are not yet generated by the live sensor platform;
- Jupiter battery-pack child devices are modeled but not yet created by the live integration;
- expansion-count increases are detectable by the declarative planner but are not yet translated into Home Assistant repairs; and
- Venus still uses temporary flat compatibility reads in the existing entity/control modules.

A later platform migration should consume `ProductProfile` entity/capability metadata directly. That migration can expose the richer Jupiter topology and then remove temporary flat compatibility surfaces.

# Diagnostics and failure handling

The coordinator serializes poll cycles with one lock, continues later poll commands after individual failures, and applies the existing module-global backoff behavior. The BLE device retains command/notification histories and per-command statistics.[^coordinator][^device]

Diagnostics serialize the product-specific coordinator data object. Existing recursive redaction continues to apply to sensitive keys.

[^init]: Integration setup and product/platform selection.
[^config-flow]: Discovery and persisted product selection.
[^coordinator]: Product-aware coordinator adapter plus inherited scheduling behavior.
[^runtime]: Generic product runtime and frame parser.
[^venus-runtime]: Venus runtime parser and polling schedule.
[^jupiter-runtime]: Jupiter runtime parser, polling schedule, and compatibility data adapter.
[^device]: Shared BLE transport and retained legacy parser implementation.
