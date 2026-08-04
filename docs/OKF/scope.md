---
type: Knowledge Scope
title: Marstek BLE knowledge scope
description: Defines the product, source, and trust boundaries for this knowledge bundle.
tags: [scope, provenance, marstek, venus]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T09:37:02Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
    title: Open Knowledge Format specification v0.2
  - id: repository
    resource: https://github.com/The-M1k3y/ha-marstek-ble/tree/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89
    title: ha-marstek-ble repository at the documented revision
  - id: readme
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/README.md
    title: Repository README
  - id: manifest
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/manifest.json
    title: Home Assistant integration manifest
---

# Included knowledge

This bundle records knowledge directly supported by the `ha-marstek-ble` repository at the `source_revision` named in the frontmatter.[^repository]

Included subjects are:

- the Home Assistant custom integration's purpose, structure, setup flow, polling model, entities, diagnostics, and BLE lifecycle;
- device discovery and behavior implemented for Marstek Venus E units advertised as `MST_ACCP_*` or `MST_VNSE3_*`; and
- BLE framing, commands, control payloads, and response layouts implemented in the repository.

The repository describes Venus E hardware v2 as tested and hardware v3 as untested.[^readme] The integration manifest registers both advertising-name patterns and identifies the integration as a local-polling device integration.[^manifest]

# Explicit exclusions

The following information MUST NOT be added to or inferred into this bundle unless it first becomes an explicit, reviewable repository source:

- any reverse engineering, packet captures, field mappings, hypotheses, or conclusions concerning Marstek Jupiter-C units;
- information remembered from conversations, private reports, diagnostics, or experiments that is not committed to this repository;
- guessed equivalence between Venus fields and fields used by another Marstek product; and
- generalized protocol claims that exceed what the current implementation demonstrates.

A product name may be mentioned only to define an exclusion or when the repository itself introduces support for that product. This scope rule prevents accidental contamination of Venus knowledge with unrelated reverse-engineering work.

# Interpretation rules

1. **Source code takes precedence.** When README prose and executable code disagree, document the behavior of the source revision and note the discrepancy.
2. **Implemented does not mean vendor-confirmed.** Field names, units, offsets, and command meanings in this bundle describe the repository's current interpretation.
3. **Overlapping or tentative interpretations stay qualified.** Do not silently upgrade comments such as “tentative,” payload-length branches, or untested device variants into confirmed protocol facts.
4. **No fabricated verification.** These concepts are machine-generated and therefore have `status: draft` and no `verified` event. Human review may add a valid `human:<id>` verification event.
5. **Revision awareness.** Before relying on a concept for code changes, compare `source_revision` with the branch being modified and inspect any intervening changes.

[^repository]: Repository tree at the documented revision.
[^readme]: Repository README.
[^manifest]: Home Assistant integration manifest.
