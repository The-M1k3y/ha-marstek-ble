---
type: Knowledge Scope
title: Marstek BLE knowledge scope
description: Defines the product, source, privacy, runtime-status, and trust boundaries for this knowledge bundle.
tags: [scope, provenance, privacy, marstek, venus, jupiter]
status: draft
source_revision: "382dc8ce426b44fbe59ef23ae50487e62774bcef"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-09T10:20:00Z }
sources:
  - id: repository
    resource: https://github.com/The-M1k3y/ha-marstek-ble/tree/382dc8ce426b44fbe59ef23ae50487e62774bcef
    title: ha-marstek-ble repository at the documented revision
  - id: runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/product_runtime.py
    title: Generic product runtime layer
  - id: products
    resource: https://github.com/The-M1k3y/ha-marstek-ble/tree/382dc8ce426b44fbe59ef23ae50487e62774bcef/custom_components/marstek_ble/products
    title: Runtime-enabled Venus and Jupiter product definitions
  - id: jupiter-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter-C Plus BLE field map
---

# Included knowledge

This bundle records knowledge directly supported by committed repository sources at the `source_revision` named in the frontmatter.[^repository]

Included subjects are:

- the Home Assistant integration's setup, polling, entities, diagnostics, BLE lifecycle, and implemented Venus protocol;
- the live product-runtime abstraction used to select Venus or Jupiter parsing, polling, model metadata, and nested cumulative data;
- declarative packet parsing, Home Assistant entity descriptions, product profiles, and topology planning;
- the sanitized Jupiter-C Plus command and field structure in committed sources; and
- fixed-limit repeated records, including Jupiter PV inputs, event history, and base/expansion battery summaries.

# Runtime-status boundary

Venus and Jupiter-C Plus are runtime-enabled products. Discovery and persisted product selection resolve to separate product runtimes, and each runtime owns its own parsing and poll schedule.[^runtime][^products]

Jupiter runtime support is currently **read-only**. It polls the observed `0x03` runtime-summary and `0x14` detailed-telemetry responses frequently and polls the observed `0x0D`, `0x08`, `0x22`, `0x21`, `0x24`, `0x04`, and `0x13` responses on the medium cadence. Commands `0x1A` and `0x1C` are not polled because the sanitized source records no observed Jupiter response structure for them.

The existing Home Assistant entity-plan generator is still not wired into the platform modules. Jupiter therefore uses a temporary compatibility adapter for safe read-only values that overlap the current legacy sensor surfaces. Unsupported Venus-only fields remain unavailable rather than receiving invented Jupiter meanings. Venus write/control platforms (`button`, `switch`, and `select`) are not loaded for Jupiter.

The declarative Jupiter model still contains richer entity metadata for PV inputs and battery-pack child devices. Those generated entities, setup-time child-device creation, and expansion-increase repairs remain a later platform migration rather than being implied by runtime enablement.

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
[^products]: Product-specific definitions and enabled product runtimes.
