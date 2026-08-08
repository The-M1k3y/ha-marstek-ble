---
type: Codebase Overview
title: ha-marstek-ble codebase overview
description: Purpose, supported discovery patterns, Home Assistant surfaces, product runtime structure, and repository layout.
tags: [home-assistant, bluetooth, integration, architecture, venus, multi-product]
status: draft
source_revision: "48ab5b3f326ae34430af3a92b7e077c0a1b38772"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-08T11:00:00Z }
sources:
  - id: init
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/__init__.py
    title: Integration setup and product selection
  - id: config-flow
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/config_flow.py
    title: Configuration and discovery flow
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/product_runtime.py
    title: Product runtime abstraction
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/product_coordinator.py
    title: Product-aware coordinator
  - id: venus
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/products/venus.py
    title: Venus product data model
  - id: venus-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/products/venus_runtime.py
    title: Venus runtime behavior
---

# Purpose

`ha-marstek-ble` is a Home Assistant custom integration for local Bluetooth Low Energy communication with Marstek energy-storage devices. The currently enabled runtime product is Venus. Multi-product infrastructure exists so additional products can define independent data models, packet parsers, polling schedules, and metadata without inheriting Venus protocol meanings.

The integration domain is `marstek_ble` and the Home Assistant IoT class is `local_polling`.

# Supported discovery surface

The currently advertised-name prefixes are Venus prefixes:

| Prefix       | Repository interpretation |
|--------------|---------------------------|
| `MST_ACCP_`  | Venus E hardware v2       |
| `MST_VNSE3_` | Venus E hardware v3       |

Newly created entries persist `product_id: venus`. The runtime registry is the selection boundary for future products. Existing entries created before product IDs were introduced remain compatible through an explicit legacy Venus fallback.[^config-flow][^init]

Jupiter declarations exist in the repository but Jupiter is not an enabled runtime and is not part of the current discovery surface.

# Home Assistant platforms

`async_setup_entry` forwards one config entry to five platforms: sensor, binary sensor, button, switch, and select.[^init]

The current platform modules remain Venus-specific. They have not yet been converted to dynamically consume `ProductProfile` entity plans. During this staged migration they read temporary flat aliases exposed by the nested `VenusData` object.

| Platform | Main responsibilities |
|----------|-----------------------|
| `sensor.py` | Battery/BMS measurements, power and energy values, capacities, temperatures, 16 cell voltages, identity, networking, and diagnostics |
| `binary_sensor.py` | Wi-Fi, MQTT, output, external-input, and smart-meter status |
| `switch.py` | Output, EPS, AC-input, generator, and buzzer commands |
| `select.py` | Operating mode, charge mode, and CT polling-rate selection |
| `button.py` | Reboot and fixed power-setting commands |

The main device registration now obtains manufacturer and model from the selected product profile. For the only enabled runtime this still resolves to `Marstek` / `Venus E`.[^init]

# Runtime data model

The live Venus coordinator stores `VenusData`, not the legacy flat `MarstekData`. `VenusData` is divided into nested sections for runtime, battery, system, timer, configuration, device information, and network information.[^venus]

`ProductProtocol` validates common frame structure and dispatches payloads through the selected `ProductRuntime`. Fixed-layout Venus responses use declarative packet metadata; Venus-specific text responses use parsers in `products/venus_runtime.py`.[^runtime][^venus-runtime]

Per-field update metadata is recorded with canonical nested paths. Flat attribute and metadata aliases remain temporarily available for the existing entity modules.

# Polling and transport

`ProductDataUpdateCoordinator` reuses the existing coordinator's scheduling, locking, availability, and backoff behavior while replacing product-dependent polling and parsing. The persistent `MarstekBLEDevice` remains the shared BLE transport.[^coordinator]

The Venus runtime owns the current fast and medium polling command sequences. A future product must supply its own runtime instead of using command-number conditionals in the coordinator.

# Repository structure

| Path | Role |
|------|------|
| `custom_components/marstek_ble/__init__.py` | Config-entry setup, runtime selection, device registration, platform forwarding, and unload |
| `custom_components/marstek_ble/config_flow.py` | Bluetooth discovery, manual selection, duplicate prevention, product-ID persistence, and polling options |
| `custom_components/marstek_ble/product_runtime.py` | Generic product runtime, poll command, frame parsing, and field metadata support |
| `custom_components/marstek_ble/product_coordinator.py` | Adapter from generic coordinator behavior to a selected product runtime |
| `custom_components/marstek_ble/schema.py` | Declarative packet/field/repeated-section parser primitives |
| `custom_components/marstek_ble/entity.py` | Product profiles, entity metadata, topology planning, and expansion-change records |
| `custom_components/marstek_ble/products/venus.py` | Canonical Venus nested dataclasses, packet schemas, and entity metadata |
| `custom_components/marstek_ble/products/venus_runtime.py` | Enabled Venus custom parsers and polling schedules |
| `custom_components/marstek_ble/products/jupiter.py` | Declarative Jupiter model; not runtime-enabled |
| `custom_components/marstek_ble/coordinator.py` | Shared inherited scheduling/backoff implementation plus retained legacy Venus poll methods |
| `custom_components/marstek_ble/marstek_device.py` | Shared BLE client/transport plus retained legacy Venus flat parser/data model |
| `custom_components/marstek_ble/{sensor,binary_sensor,switch,select,button}.py` | Existing Venus Home Assistant entity/control platforms |
| `custom_components/marstek_ble/diagnostics.py` | Redacted Home Assistant diagnostics export |

# Configuration

The options flow exposes two intervals:

- fast polling: `1–60 s`, default `1 s`;
- medium polling: `5–300 s`, default `60 s`, and never below the fast interval.

The medium cadence is represented as an integer number of fast cycles, rounded upward by the inherited coordinator behavior.

[^init]: Integration setup and product selection.
[^config-flow]: Configuration and discovery flow.
[^runtime]: Generic product runtime.
[^coordinator]: Product-aware coordinator adapter.
[^venus]: Venus product model.
[^venus-runtime]: Venus runtime behavior.
