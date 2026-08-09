---
type: Knowledge Scope
title: Marstek BLE knowledge scope
description: Defines the product, source, privacy, runtime-status, and trust boundaries for this knowledge bundle.
tags: [scope, provenance, privacy, marstek, venus, jupiter]
status: draft
source_revision: "112abd322722b2e84bcdf34ee4b0325bf14b7313"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-09T10:45:00Z }
sources:
  - id: repository
    resource: https://github.com/The-M1k3y/ha-marstek-ble/tree/112abd322722b2e84bcdf34ee4b0325bf14b7313
    title: ha-marstek-ble repository at the documented revision
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/product_runtime.py
    title: Generic product runtime layer
  - id: entity-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/product_entity_platform.py
    title: Runtime declarative entity synchronization
  - id: products
    resource: https://github.com/The-M1k3y/ha-marstek-ble/tree/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/products
    title: Runtime-enabled Venus and Jupiter product definitions
  - id: jupiter-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter-C Plus BLE field map
---

# Included knowledge

This bundle records knowledge directly supported by committed repository sources at the `source_revision` named in the frontmatter.[^repository]

Included subjects are:

- Home Assistant setup, discovery, polling, entities, controls, diagnostics, and BLE lifecycle;
- runtime selection and product-specific parsing for Venus and Jupiter-C Plus;
- declarative packet parsing and live sensor/binary-sensor generation from product profiles;
- the sanitized Jupiter-C Plus command and field structure; and
- fixed-limit repeated records, including Jupiter PV inputs, event history, and base/expansion battery summaries.

# Runtime-status boundary

Venus and Jupiter-C Plus are runtime-enabled products. Discovery and persisted product selection resolve to separate product runtimes, and each runtime owns its own parsing and poll schedule.[^runtime][^products]

Jupiter support is currently **read-only**. It polls `0x03` and `0x14` on the fast cadence and the observed `0x0D`, `0x08`, `0x22`, `0x21`, `0x24`, `0x04`, and `0x13` responses on the medium cadence. Commands `0x1A` and `0x1C` are not polled because the sanitized source records no observed Jupiter response structure for them.

Sensor and binary-sensor platforms now consume `ProductProfile` entity plans. Jupiter therefore exposes its modeled aggregate telemetry, four PV inputs, derived values, and populated battery-pack records. Battery-pack child devices use stable positional identifiers. New pack slots are added when a later `pack_count` increase is observed; a later decrease keeps the already-created entity identity but marks it unavailable through the repeated-record presence binding.[^entity-runtime]

Venus write/control platforms (`button`, `switch`, and `select`) are not loaded for Jupiter because their command semantics have not been validated for that product.

# Privacy and sanitization boundary

Repository protocol knowledge may include command numbers, payload lengths, offsets, signedness, byte order, binary types, semantic field names, canonical units, confidence labels, repeated-record counts, strides, and topology.

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

The generic schema, runtime, coordinator adapter, and entity infrastructure are shared mechanisms. Product modules provide actual packet definitions, parsing exceptions, polling schedules, repeated limits, and Home Assistant metadata.

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
[^entity-runtime]: Runtime declarative entity synchronization.
[^products]: Product-specific definitions and enabled product runtimes.
