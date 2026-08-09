---
type: Software Architecture
title: Declarative product, parsing, and entity model
description: Product-specific packet schemas, cumulative dataclasses, runtime parsing, generated Home Assistant entity metadata, repeated records, and expansion topology.
tags: [architecture, dataclass, parsing, entities, products, expansions]
status: draft
source_revision: "382dc8ce426b44fbe59ef23ae50487e62774bcef"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-09T10:20:00Z }
sources:
  - id: schema
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/schema.py
    title: Declarative packet and dataclass parsing primitives
  - id: entities
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/entity.py
    title: Entity metadata and topology planning
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/product_runtime.py
    title: Generic runtime adapter
  - id: venus-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/products/venus_runtime.py
    title: Enabled Venus runtime
  - id: jupiter
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/products/jupiter.py
    title: Jupiter declarative model
  - id: jupiter-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/products/jupiter_runtime.py
    title: Enabled Jupiter runtime adapter
---

# Status

The declarative parsing model is live for both Venus and Jupiter-C Plus. Both products use product-specific dataclasses, packet schemas, the generic runtime parser, and product-owned polling schedules.

The entity-planning layer remains scaffolding: the existing Home Assistant sensor and binary-sensor modules have not yet been replaced by generated `ProductProfile` entity plans. Jupiter therefore uses a temporary read-only compatibility adapter for the overlapping legacy sensor surface. Venus write/control platforms are not loaded for Jupiter.

# Single source of truth

Each product model combines:

1. packet schemas and field sources;
2. nested dataclasses representing cumulative state; and
3. Home Assistant entity descriptions attached to destination fields.

A field may define one `FieldSource` per packet. Every source normalizes its raw representation to the field's canonical unit. Parsing updates only fields represented by the selected packet and leaves all others unchanged.

Direct entity metadata is attached to the same dataclass field as its packet sources. Derived entities remain profile metadata because they depend on multiple fields and should not be cached as mutable state.

# Runtime adapters

`ProductRuntime` binds one `ProductProfile` to runtime behavior that cannot be represented by fixed binary field metadata alone:

- fast polling commands;
- medium polling commands; and
- optional command-specific payload parsers for text or otherwise irregular responses.

`ProductProtocol` owns common Marstek frame validation and dispatches the payload only to the selected runtime. Runtime products are registered explicitly, preventing one product from accidentally inheriting another product's command meanings.

Venus and Jupiter each define independent polling schedules. Jupiter deliberately omits commands with no observed response structure in the sanitized product source, even when Venus uses those command numbers.

# Parsing

`PacketSchema` validates command-specific payload lengths. `FieldSource` defines an offset, explicit byte order, `struct` format, optional length gates, and a converter. Declarative parsing decodes all matching fields before applying updates, so a decoding error cannot leave the data object partially modified.

Nested dataclasses are traversed recursively. `RepeatedSectionSource` adds a base offset and stride for fixed-limit repeated records. Parsed paths retain list indices, for example:

```text
battery.packs.1.highest_cell_voltage
pv_inputs.3.power
```

Both enabled runtimes use canonical paths for update metadata. Venus exposes temporary flat aliases required by the existing entity implementation. `RuntimeJupiterData` now does the same only for legacy fields that have a safe Jupiter equivalent; incompatible Venus-only fields remain unavailable.

# Jupiter runtime state

The canonical declarative Jupiter model contains:

- runtime summary values;
- energy counters;
- inverter and grid telemetry;
- MPPT telemetry;
- four PV-input records;
- aggregate BMS telemetry;
- four fixed battery-pack summary slots;
- twenty event-history records;
- device identity; and
- unresolved one-byte status responses.

The runtime adapter additionally parses comma-separated `0x04` device information and the variable-length `0x08` Wi-Fi SSID payload. It tracks per-field update metadata and provides temporary compatibility reads for the current Home Assistant sensor modules.

# Entity planning

`ProductProfile.build_entity_plan()` recursively discovers field metadata and returns an immutable startup plan containing:

- device bindings;
- entity bindings;
- direct paths or derived-value functions;
- stale-data dependencies;
- stable product-local unique keys; and
- configured repeated-record counts.

Indexed scalar expansion creates several entities from one sequence on the same device, such as Venus cell voltages. Repeated nested dataclasses represent records containing several values, such as Jupiter battery summaries.

This entity plan is still not used by the live Home Assistant platform modules.

# Child devices and expansion discovery

A repeated section may define `RepeatedChildDeviceSpec`. The startup plan then creates one child-device binding per populated record. Jupiter uses position indices for the base battery and up to three expansion slots.

The plan snapshots the count during setup or explicit reconfiguration. Existing bindings include a runtime presence predicate, so a later decrease can make a child unavailable without shifting identities.

`detect_expansion_increases()` compares later telemetry with the startup plan and returns `ExpansionChange` records. The live Jupiter parser now populates the underlying pack-count and repeated-record data, but child-device creation and Home Assistant repair signaling remain unwired until the entity-platform migration.
