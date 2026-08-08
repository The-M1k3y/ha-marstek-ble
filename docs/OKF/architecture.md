---
type: Software Architecture
title: Marstek BLE runtime architecture
description: Product selection, polling, BLE lifecycle, product-specific parsing, state propagation, diagnostics, and remaining migration boundaries.
tags: [architecture, coordinator, polling, bluetooth, multi-product]
status: draft
source_revision: "48ab5b3f326ae34430af3a92b7e077c0a1b38772"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-08T11:00:00Z }
sources:
  - id: init
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/__init__.py
    title: Integration setup and product selection
  - id: config-flow
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/config_flow.py
    title: Discovery and persisted product selection
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/product_coordinator.py
    title: Product-aware coordinator adapter
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/product_runtime.py
    title: Generic product runtime and frame parser
  - id: venus-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/products/venus_runtime.py
    title: Venus parsing and polling runtime
  - id: venus-data
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/products/venus.py
    title: Venus nested dataclasses and packet schemas
  - id: device
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/marstek_device.py
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
                         (`VenusData` today)
                                  │
                                  ▼
                       CoordinatorEntity platforms
```

The live integration now selects an explicit product runtime. New config entries persist the selected `product_id`; entries created before this migration have no product ID and retain a Venus fallback for compatibility. A persisted unknown product ID is rejected instead of being interpreted as Venus.[^init][^config-flow]

Only the Venus runtime is enabled. The Jupiter declarative model remains separate scaffolding and is intentionally absent from the runtime registry.

# Coordinator and BLE transport boundary

`ProductDataUpdateCoordinator` subclasses the existing coordinator to reuse scheduling, backoff, polling locks, availability handling, and the persistent `MarstekBLEDevice`. It replaces only the product-dependent pieces:

- cumulative data object;
- notification protocol/parser; and
- fast and medium command schedules.[^coordinator]

`MarstekBLEDevice` remains the shared transport. It owns connection establishment, notification subscription, command serialization, response waiting, retry behavior, diagnostics history, and disconnect handling.[^device]

The old flat `MarstekData` and `MarstekProtocol` remain in `marstek_device.py` for compatibility and regression coverage, but config-entry setup no longer uses them as the live coordinator state/parser.

# Venus polling

The enabled Venus runtime defines the same polling schedule previously embedded in the coordinator.[^venus-runtime]

## Fast poll

At every configured fast interval:

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

`0x1C` is still polled but has no enabled Venus payload parser, so it does not update the cumulative data snapshot.

# Product-specific parsing and state

`ProductProtocol` performs common Marstek frame validation: minimum frame size, start/type bytes, declared frame length, and XOR checksum. It then dispatches the payload to the selected `ProductRuntime`.[^runtime]

Fixed binary Venus packets use the declarative `PacketSchema` / `FieldSource` traversal. Text-like packets that require key/value parsing use Venus-specific payload functions. These parsers remain in the Venus runtime rather than the generic protocol layer so identical command bytes on another product do not imply identical semantics.[^venus-runtime]

The canonical live Venus snapshot is `VenusData`, composed of nested sections:

- `runtime`;
- `battery`;
- `system`;
- `timer`;
- `configuration`;
- `device`; and
- `network`.[^venus-data]

Updates record canonical data paths such as `battery.battery_soc` together with source-command/timestamp metadata. The Venus data class temporarily exposes flat read aliases such as `battery_soc` and legacy metadata aliases, allowing the existing entity/control modules to keep working while those platforms are migrated separately. These aliases are compatibility surfaces, not the canonical product model.

# Product selection and future products

Runtime-enabled products are registered explicitly. Product selection has two stages:

1. discovery maps an advertised local name to an enabled runtime and persists its stable product ID;
2. setup resolves that ID back to the runtime before creating the coordinator.[^config-flow][^init]

Adding another runtime therefore requires an explicit registry entry and product-specific discovery support; it must not inherit Venus parsing or polling merely because command numbers overlap. Discovery patterns, protocol schemas, poll commands, device metadata, capabilities, entity topology, and expansion limits remain product concerns.

# Remaining migration boundaries

The following surfaces are intentionally not generalized by this change:

- Home Assistant entity platform declarations are still the existing Venus definitions and consume the temporary flat compatibility reads;
- control command constants and platform implementations remain Venus-oriented;
- Jupiter remains declarative-only and is not enabled at runtime;
- the old Venus parser/data classes remain for compatibility and regression tests.

A later platform migration should consume `ProductProfile` entity/capability metadata directly and then remove the flat Venus compatibility layer when no callers depend on it.

# Diagnostics and failure handling

The inherited coordinator still serializes poll cycles with one lock, continues later poll commands after individual failures, and applies the existing module-global backoff behavior. The BLE device still retains command/notification histories and per-command statistics.[^coordinator][^device]

Diagnostics serialize the coordinator data object. For the live Venus coordinator this is now the nested `VenusData` structure rather than the old flat snapshot. Existing redaction still applies recursively to sensitive keys.

[^init]: Integration setup and product selection.
[^config-flow]: Discovery and persisted product selection.
[^coordinator]: Product-aware coordinator adapter plus inherited scheduling behavior.
[^runtime]: Generic product runtime and frame parser.
[^venus-runtime]: Venus runtime parser and polling schedule.
[^venus-data]: Venus product dataclasses and packet definitions.
[^device]: Shared BLE transport and retained legacy parser implementation.
