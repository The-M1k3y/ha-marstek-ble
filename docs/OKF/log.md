# Marstek BLE OKF update log

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
