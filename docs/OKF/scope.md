---
type: Knowledge Scope
title: Marstek BLE knowledge scope
description: Defines the product, source, privacy, and trust boundaries for this knowledge bundle.
tags: [scope, provenance, privacy, marstek, venus, jupiter]
status: draft
source_revision: "17d3211e12989eb428681f5959707e9403e61bf6"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-05T14:19:00Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
    title: Open Knowledge Format specification v0.2
  - id: repository
    resource: https://github.com/The-M1k3y/ha-marstek-ble/tree/17d3211e12989eb428681f5959707e9403e61bf6
    title: ha-marstek-ble repository at the documented revision
  - id: existing-device
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/marstek_device.py
    title: Existing Venus-specific protocol implementation
  - id: declarative-schema
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/schema.py
    title: Branch-only declarative parsing scaffolding
  - id: product-models
    resource: https://github.com/The-M1k3y/ha-marstek-ble/tree/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/products
    title: Branch-only Venus and Jupiter product models
  - id: jupiter-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter-C Plus BLE field map
---

# Included knowledge

This bundle records knowledge directly supported by committed repository sources
at the `source_revision` named in the frontmatter.[^repository]

Included subjects are:

- the existing Home Assistant integration's setup, polling, entities,
  diagnostics, BLE lifecycle, and implemented Venus protocol;
- branch-only declarative packet parsing, cumulative nested dataclasses, Home
  Assistant entity descriptions, and product profiles;
- the sanitized Jupiter-C Plus command and field structure in the committed
  field map; and
- fixed-limit repeated records, including Jupiter PV inputs, event history, and
  base/expansion battery summaries.

The declarative model is scaffolding only. It does not mean Jupiter is currently
discovered, polled, parsed, or exposed by the running integration.

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

A shared command byte does not establish a shared payload schema. Venus and
Jupiter offsets, scales, status fields, packet lengths, response availability,
and entities remain product-specific unless a committed source explicitly
supports a common abstraction.

The generic schema and entity planners are shared mechanisms. Product modules
provide actual packet definitions, capabilities, repeated limits, and Home
Assistant metadata.

# Interpretation rules

1. **Executable source takes precedence.** When documentation and code disagree,
   inspect the current branch and update the knowledge.
2. **Sanitized sources constrain product facts.** Do not add capture-derived
   values or interpretations absent from committed sanitized sources.
3. **Implemented does not mean vendor-confirmed.** Field meanings describe the
   repository's current interpretation.
4. **Confidence remains explicit.** Tentative and strong mappings must not be
   silently upgraded to confirmed.
5. **No fabricated verification.** Machine-generated concepts remain `draft`
   until a human actually reviews them.
6. **Revision awareness.** Compare `source_revision` with the branch before
   relying on a concept for code changes.

[^repository]: Repository tree at the documented revision.
