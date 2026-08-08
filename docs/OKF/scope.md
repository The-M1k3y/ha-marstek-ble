---
type: Knowledge Scope
title: Marstek BLE knowledge scope
description: Defines the product, source, privacy, runtime-status, and trust boundaries for this knowledge bundle.
tags: [scope, provenance, privacy, marstek, venus, jupiter]
status: draft
source_revision: "48ab5b3f326ae34430af3a92b7e077c0a1b38772"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-08T11:00:00Z }
sources:
  - id: repository
    resource: https://github.com/The-M1k3y/ha-marstek-ble/tree/48ab5b3f326ae34430af3a92b7e077c0a1b38772
    title: ha-marstek-ble repository at the documented revision
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/product_runtime.py
    title: Generic product runtime layer
  - id: venus
    resource: https://github.com/The-M1k3y/ha-marstek-ble/tree/48ab5b3f326ae34430af3a92b7e077c0a1b38772/custom_components/marstek_ble/products
    title: Product-specific models and enabled Venus runtime
  - id: jupiter-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter-C Plus BLE field map
---

# Included knowledge

This bundle records knowledge directly supported by committed repository sources at the `source_revision` named in the frontmatter.[^repository]

Included subjects are:

- the Home Assistant integration's setup, polling, entities, diagnostics, BLE lifecycle, and implemented Venus protocol;
- the live product-runtime abstraction used to select Venus parsing, polling, model metadata, and nested cumulative data;
- declarative packet parsing, Home Assistant entity descriptions, product profiles, and topology planning;
- the sanitized Jupiter-C Plus command and field structure in committed sources; and
- fixed-limit repeated records, including Jupiter PV inputs, event history, and base/expansion battery summaries.

# Runtime-status boundary

The Venus product model is runtime-enabled. Its nested `VenusData` dataclasses are the canonical live coordinator state and its `ProductRuntime` owns parsing and poll schedules.[^runtime][^venus]

Jupiter remains declarative-only. Its presence in `products/jupiter.py` and the OKF does **not** mean Jupiter is currently discovered, selected, polled, parsed, or exposed by Home Assistant. Do not infer runtime support from declarative definitions alone.

The Home Assistant entity-plan generator is also not yet wired into the platform modules. Existing Venus entity/control modules currently rely on temporary flat compatibility reads from `VenusData`.

# Privacy and sanitization boundary

Repository protocol knowledge may include:

- command numbers and payload lengths;
- payload-relative offsets and lengths;
- signedness, byte order, and binary types;
- semantic field names and canonical units;
- confidence labels; and
- repeated-record counts, strides, and topology.

The following private diagnostic material is explicitly excluded:

- complete frames or payload hex;
- captured timestamps and event records;
- device, cloud, account, or network identifiers;
- MAC addresses and Wi-Fi names;
- observed telemetry values or capture-specific counter values; and
- source diagnostic files or reconstructions of their contents.

The Jupiter map intentionally retains protocol structure without capture data.

# Product separation

A shared command byte does not establish a shared payload schema. Venus and Jupiter offsets, scales, status fields, packet lengths, response availability, polling schedules, controls, and entities remain product-specific unless a committed source explicitly supports a common abstraction.

The generic schema, runtime, coordinator adapter, and entity planners are shared mechanisms. Product modules provide actual packet definitions, parsing exceptions, polling schedules, capabilities, repeated limits, and Home Assistant metadata.

Persisted `product_id` values identify the selected runtime. An unknown persisted product ID must not fall back to Venus; legacy entries without a product ID retain the Venus fallback for migration compatibility.

# Interpretation rules

1. **Executable source takes precedence.** When documentation and code disagree, inspect the current branch and update the knowledge.
2. **Sanitized sources constrain product facts.** Do not add capture-derived values or interpretations absent from committed sanitized sources.
3. **Implemented does not mean vendor-confirmed.** Field meanings describe the repository's current interpretation.
4. **Confidence remains explicit.** Tentative and strong mappings must not be silently upgraded to confirmed.
5. **No fabricated verification.** Machine-generated concepts remain `draft` until a human actually reviews them.
6. **Revision awareness.** Compare `source_revision` with the branch before relying on a concept for code changes.

[^repository]: Repository tree at the documented revision.
[^runtime]: Generic product runtime implementation.
[^venus]: Product-specific definitions and enabled Venus runtime.
