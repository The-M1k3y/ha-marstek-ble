# Marstek BLE OKF update log

## 2026-08-09

- **Jupiter runtime**: Enabled Jupiter-C Plus as the `jupiter_c_plus` runtime product and added `MST_JPLS_*` Bluetooth discovery.
- **Polling**: Added Jupiter-owned fast polling for `0x03`/`0x14` and medium polling for the observed `0x0D`, `0x08`, `0x22`, `0x21`, `0x24`, `0x04`, and `0x13` responses. Jupiter `0x1A` and `0x1C` remain unpolled because no response structure is retained in the sanitized source.
- **Parsing**: Connected the existing declarative Jupiter binary schemas to the live product protocol and added product-local parsers for `0x04` device information and `0x08` Wi-Fi SSID.
- **Compatibility**: Added tracked Jupiter runtime data and temporary flat read/metadata aliases only where the current legacy sensor surface has a safe Jupiter equivalent; unsupported Venus-only values remain unavailable.
- **Controls**: Limited Jupiter to sensor and binary-sensor platforms. Venus button, switch, and select command semantics are not exposed for Jupiter.
- **Tests**: Added a new Jupiter-only runtime test module without modifying existing tests. One pre-existing runtime-registry test still asserts the former invariant that `MST_JPLS_*` is unsupported and therefore conflicts with this feature by design.
- **Entity migration boundary**: The declarative per-PV entities, battery-pack child devices, and expansion repair adapter remain modeled but are not yet wired into Home Assistant platform setup.

## 2026-08-08

- **Venus runtime migration**: Connected the Venus declarative packet/dataclass model to the live integration through a generic product runtime and product-aware coordinator adapter.
- **Product selection**: Added explicit runtime registration and persisted `product_id` selection for new config entries; legacy entries without a product ID retain the Venus fallback, while unknown persisted products are rejected.
- **Polling**: Moved the Venus fast and medium command schedules out of the generic coordinator and into `VENUS_RUNTIME`.
- **Parsing**: Fixed-layout Venus responses now use declarative field sources; Venus-specific text responses remain product-local custom parsers.
- **State model**: The live Venus coordinator now stores nested `VenusData`. Temporary flat read/metadata aliases preserve compatibility with the not-yet-migrated Venus entity platforms.
- **Product isolation**: Jupiter remains declarative-only and is deliberately excluded from the enabled runtime registry.
- **Tests**: Added isolated tests for runtime registration, parsing, field metadata, poll dispatch, product selection, compatibility behavior, and failure/boundary cases; updated repository contracts and isolated Home Assistant stubs for the now-imported product metadata.
- **Declarative coverage tests**: Added direct tests for schema validation and failure paths, entity-plan topology and presence logic, and the declarative Jupiter runtime-summary, detailed-telemetry, event-history, repeated battery-pack, expansion, and derived-entity behavior.
- **Coverage**: Removed the final Jupiter omission. Coverage now includes every Python source file under `custom_components/marstek_ble` and `standalone_test` with no file-level exceptions.
- **Testing policy**: Added a dedicated testing-and-coverage OKF concept and updated `Agents.md` to prohibit coverage omissions and to use uncovered statements and branches as test-design input rather than exclusion criteria.

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
