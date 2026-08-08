# Marstek BLE OKF update log

## 2026-08-08

- **Venus runtime migration**: Connected the Venus declarative packet/dataclass model to the live integration through a generic product runtime and product-aware coordinator adapter.
- **Product selection**: Added explicit runtime registration and persisted `product_id` selection for new config entries; legacy entries without a product ID retain the Venus fallback, while unknown persisted products are rejected.
- **Polling**: Moved the Venus fast and medium command schedules out of the generic coordinator and into `VENUS_RUNTIME`.
- **Parsing**: Fixed-layout Venus responses now use declarative field sources; Venus-specific text responses remain product-local custom parsers.
- **State model**: The live Venus coordinator now stores nested `VenusData`. Temporary flat read/metadata aliases preserve compatibility with the not-yet-migrated Venus entity platforms.
- **Product isolation**: Jupiter remains declarative-only and is deliberately excluded from the enabled runtime registry.
- **Tests**: Added isolated tests for runtime registration, parsing, field metadata, poll dispatch, product selection, compatibility behavior, and failure/boundary cases; updated repository contracts and isolated Home Assistant stubs for the now-imported product metadata.
- **Coverage**: Removed migrated schema/entity/Venus runtime modules from coverage exclusions; only the unwired Jupiter product model remains excluded.

## 2026-08-05

- **Architecture**: Added branch-only declarative packet, dataclass, entity-description, product-profile, repeated-record, and child-device scaffolding.
- **Products**: Added declarative Venus and Jupiter-C Plus definitions without connecting them to the existing integration runtime.
- **Expansions**: Added fixed-limit Jupiter battery-pack records, setup-time child-device planning, slot-based identifiers, runtime presence checks, and expansion-increase records for a future Home Assistant repair adapter.
- **Jupiter protocol**: Added a sanitized structural field map and progressive OKF hierarchy for runtime, event history, detailed telemetry, unresolved responses, and battery expansions.
- **Privacy**: Prohibited committing raw captures, frames, payload hex, capture timestamps, identifiers, Wi-Fi names, observed values, counters, or event records.

## 2026-08-04

- **Update**: Added a progressive `protocol/venus/messages/` hierarchy with one focused concept for every BLE message sent or parsed by the integration.
- **Update**: Documented request and response fields by byte offset, including length, type, name, unit, descriptions, unknown gaps, ignored suffixes, and overlapping interpretations.
- **Update**: Refactored the command reference into a compact inventory linking to the detailed message concepts.
- **Update**: Required aligned Markdown tables and byte-offset ordering in `Agents.md`.
- **Initialization**: Created the OKF v0.2 knowledge bundle from repository revision `59ea1c3f0e6f239cecbae7f9024e0dc48c328d89`.
- **Creation**: Added codebase, architecture, Venus BLE transport, and Venus command/payload references.
- **Scope**: Explicitly excluded Jupiter-C reverse-engineering material and any information not present in repository sources.
