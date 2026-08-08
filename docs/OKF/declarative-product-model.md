---
type: Software Architecture
title: Declarative product, parsing, and entity model
description: Product-specific packet schemas, cumulative dataclasses, runtime parsing, generated Home Assistant entity metadata, repeated records, and expansion topology.
tags: [architecture, dataclass, parsing, entities, products, expansions]
status: draft
source_revision: "48ab5b3f326ae34430af3a92b7e077c0a1b38772"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-08T11:00:00Z }
sources:
  - id: schema
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/schema.py
    title: Declarative packet and dataclass parsing primitives
  - id: entities
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/entity.py
    title: Entity metadata and topology planning
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/product_runtime.py
    title: Generic runtime adapter
  - id: venus
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/products/venus.py
    title: Venus product model
  - id: venus-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/products/venus_runtime.py
    title: Enabled Venus runtime
  - id: jupiter
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/products/jupiter.py
    title: Jupiter declarative model
---

# Status

The declarative model is now partially live. Venus uses the product-specific dataclasses, packet schemas, generic runtime parser, and product-owned polling schedule in the integration runtime. Jupiter remains declarative-only and is intentionally not registered as an enabled runtime.

The entity-planning layer is still scaffolding: the existing Home Assistant entity modules have not yet been replaced by generated `ProductProfile` entity plans.

# Single source of truth

Each product model combines:

1. packet schemas and field sources;
2. nested dataclasses representing cumulative state; and
3. Home Assistant entity descriptions attached to destination fields.

A field may define one `FieldSource` per packet. Every source normalizes its raw representation to the field's canonical unit. Parsing updates only fields represented by the selected packet and leaves all others unchanged.

Direct entity metadata is attached to the same dataclass field as its packet sources. Derived entities remain profile metadata because they depend on multiple fields and should not be cached as mutable state.

# Runtime adapter

`ProductRuntime` binds one `ProductProfile` to runtime behavior that cannot be represented by fixed binary field metadata alone:

- fast polling commands;
- medium polling commands; and
- optional command-specific payload parsers for text or otherwise irregular responses.

`ProductProtocol` owns the common Marstek frame validation and dispatches the payload only to the selected runtime. Runtime products are registered explicitly, which prevents an unimplemented product from accidentally inheriting Venus command meanings.

`PollCommand` carries a command byte, optional payload, and response-window delay. Poll schedules are therefore data owned by the product runtime rather than hard-coded coordinator branches.

# Parsing

`PacketSchema` validates command-specific payload lengths. `FieldSource` defines an offset, explicit byte order, `struct` format, optional length gates, and a converter. Declarative parsing decodes all matching fields before applying updates, so a decoding error cannot leave the data object partially modified.

Nested dataclasses are traversed recursively. `RepeatedSectionSource` adds a base offset and stride for fixed-limit repeated records. Parsed paths retain list indices, for example:

```text
battery.packs.1.highest_cell_voltage
pv_inputs.3.power
```

The enabled Venus runtime uses these paths for source timestamp/staleness metadata. It also exposes temporary flat metadata aliases required by the existing entity implementation.

# Venus migration state

`VenusData` is the canonical live coordinator snapshot. It contains nested runtime, battery, system, timer, configuration, device-information, and network sections.

Fixed-layout responses are parsed from the dataclass field metadata. Venus-specific text responses remain in `products/venus_runtime.py`, including device information, Wi-Fi SSID, meter IP, network information, and local API status.

The existing entity/control modules still expect flat attributes. `VenusData` therefore provides temporary read-only flat aliases such as `battery_soc` and `wifi_connected`. New runtime code should use the nested canonical paths instead; the compatibility aliases are intended to disappear after the entity platforms migrate.

# Entity planning

`ProductProfile.build_entity_plan()` recursively discovers field metadata and returns an immutable startup plan containing:

- device bindings;
- entity bindings;
- direct paths or derived-value functions;
- stale-data dependencies;
- stable product-local unique keys; and
- configured repeated-record counts.

Indexed scalar expansion creates several entities from one sequence on the same device, such as Venus cell voltages. Repeated nested dataclasses represent records containing several values, such as Jupiter battery summaries.

This entity plan is not yet used by the live Home Assistant platform modules.

# Child devices and expansion discovery

A repeated section may define `RepeatedChildDeviceSpec`. The startup plan then creates one child-device binding per populated record. Jupiter uses position indices for the base battery and up to three expansion slots.

The plan snapshots the count during setup or explicit reconfiguration. Existing bindings include a runtime presence predicate, so a later decrease can make a child unavailable without shifting identities.

`detect_expansion_increases()` compares later telemetry with the startup plan and returns `ExpansionChange` records. A future integration adapter can convert these into Home Assistant repairs requesting a reload or reconfiguration. Jupiter runtime parsing, child-device creation, and repairs remain unwired.
