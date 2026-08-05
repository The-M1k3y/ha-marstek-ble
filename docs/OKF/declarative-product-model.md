---
type: Software Architecture
title: Declarative product, parsing, and entity model
description: Branch-only scaffolding for packet schemas, cumulative product data, generated Home Assistant entities, repeated records, and expansion topology.
tags: [architecture, dataclass, parsing, entities, products, expansions]
status: draft
source_revision: "17d3211e12989eb428681f5959707e9403e61bf6"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-05T14:19:00Z }
sources:
  - id: schema
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/schema.py
    title: Declarative packet and dataclass parsing scaffolding
  - id: entities
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/entity.py
    title: Entity metadata and topology planning
  - id: venus
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/products/venus.py
    title: Venus product model
  - id: jupiter
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/products/jupiter.py
    title: Jupiter product model
---

# Status

The model is scaffolding on `multi-product-support`. Existing protocol,
coordinator, setup, and entity-platform modules do not import or execute it. No
pre-existing integration source file was modified.

# Single source of truth

Each product module combines:

1. packet schemas and field sources;
2. nested dataclasses representing cumulative state; and
3. Home Assistant entity descriptions attached to their destination fields.

A field may define one `FieldSource` per packet. Every source normalizes its raw
representation to the field's canonical unit. Parsing updates only fields
represented by the selected packet and leaves all others unchanged.

Direct entity metadata is attached to the same dataclass field as its packet
sources, preventing string-based mismatches. Derived entities remain profile
metadata because they depend on multiple fields and should not be cached as
mutable state.

# Parsing

`PacketSchema` validates command-specific payload lengths. `FieldSource` defines
an offset, explicit byte order, `struct` format, optional length gates, and a
converter. `parse_into()` decodes all matching fields before applying any update,
so an exception cannot leave the data object partially modified.

Nested dataclasses are traversed recursively. `RepeatedSectionSource` adds a
base offset and stride for fixed-limit repeated records. Parsed paths retain list
indices, for example:

```text
battery.packs.1.highest_cell_voltage
pv_inputs.3.power
```

These paths can later be reused for source timestamps and stale-data tracking.

# Entity planning

`ProductProfile.build_entity_plan()` recursively discovers field metadata and
returns an immutable startup plan containing:

- device bindings;
- entity bindings;
- direct paths or derived-value functions;
- stale-data dependencies;
- stable product-local unique keys; and
- configured repeated-record counts.

Indexed scalar expansion creates several entities from one sequence on the same
device, such as Venus cell voltages. Repeated nested dataclasses represent
records containing several values, such as Jupiter battery summaries.

# Child devices and expansion discovery

A repeated section may define `RepeatedChildDeviceSpec`. The startup plan then
creates one child-device binding per populated record. Jupiter uses position
indices for the base battery and up to three expansion slots.

The plan snapshots the count during setup or explicit reconfiguration. Existing
bindings include a runtime presence predicate, so a later decrease can make a
child unavailable without shifting identities.

`detect_expansion_increases()` compares later telemetry with the startup plan and
returns `ExpansionChange` records. The eventual integration adapter can convert
these into Home Assistant warning repairs requesting a reload or reconfiguration.
This scaffolding intentionally does not create repairs or runtime entities yet.
