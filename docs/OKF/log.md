# Marstek BLE OKF update log

## 2026-08-10

- **Unverified diagnostics**: Exposed Jupiter fields with `Strong` or `Tentative` interpretations as diagnostic sensors so their long-term changes can be correlated without presenting the meanings as verified telemetry. This includes strong inverter/MPPT/BMS values, battery-pack summaries, and the tentative base/PE voltage fields.
- **Event observation**: Exposed all seven interpreted fields of each of the twenty fixed `0x13` event-history slots as diagnostic sensors. Physical slot order is preserved and no chronological or Home Assistant event semantics are inferred.
- **Unknown-field boundary**: Kept fields with no current Jupiter-specific semantic hypothesis unexposed, including detailed-telemetry offset `0x08`, unresolved `0x0D`, and raw `0x21`/`0x22`/`0x24` response bytes.
- **Tests**: Added entity-contract coverage for the unverified diagnostic set, event-slot diagnostics, tentative base/PE parsing, and the boundary that wholly unresolved fields remain hidden.
- **Battery state**: Reclassified Jupiter `0x03` offset `0x12` from a boolean charging flag to a three-state field: `0` idle, `1` charging, and `2` discharging. Unknown raw values remain unresolved.
- **Entities**: Replaced the misleading `Battery Charging Active` binary entity with a `Battery State` sensor and removed the redundant battery-power-derived charging binary sensor. The signed `Battery Power` sensor remains available.
- **Grid telemetry**: Withdrew the `Grid Current` entity because controlled Jupiter behavior contradicted the previous interpretation of `0x14` offset `0x08`; the field remains available internally for further protocol investigation.
- **Display metadata**: Set grid frequency to two suggested decimal places and renamed the identity sensor to `Bluetooth MAC Address`.
- **Tests**: Added regression coverage for all verified battery-state values, unknown-state handling, removed charging binaries, grid-current suppression, frequency precision, and Bluetooth MAC naming.

## 2026-08-09

- **Jupiter runtime**: Enabled Jupiter-C Plus as the `jupiter_c_plus` runtime product and added `MST_JPLS_*` Bluetooth discovery.
- **Polling**: Added Jupiter-owned fast polling for `0x03`/`0x14` and medium polling for the observed `0x0D`, `0x08`, `0x22`, `0x21`, `0x24`, `0x04`, and `0x13` responses. Jupiter `0x1A` and `0x1C` remain unpolled because no response structure is retained in the sanitized source.
- **Parsing**: Connected the declarative Jupiter binary schemas to the live protocol and added product-local parsers for `0x04` device information and `0x08` Wi-Fi SSID.
- **Entities**: Connected sensor and binary-sensor platforms to `ProductProfile` plans. Jupiter now exposes its modeled PV, inverter, energy, BMS, and derived read-only entities without inheriting Venus field definitions.
- **Battery topology**: Populated base/expansion battery records create stable positional child devices. New positions are added on later count increases; positions that disappear become unavailable without renumbering existing children.
- **Controls**: Jupiter remains read-only. Venus button, switch, and select command semantics are not exposed for Jupiter.
- **Compatibility**: Retained tracked Jupiter compatibility aliases and legacy entity constructors for transition/regression callers; canonical product bindings are now the live sensor path.
- **Tests**: Added Jupiter runtime, dynamic entity-manager, and live declarative entity tests. Updated the existing runtime-registry test to verify that every declared discovery prefix resolves to an enabled runtime, including Jupiter-C Plus.

## 2026-08-08

- **Venus runtime migration**: Connected the Venus declarative packet/dataclass model to the live integration through a generic product runtime and product-aware coordinator adapter.
- **Product selection**: Added explicit runtime registration and persisted `product_id` selection for new config entries; legacy entries without a product ID retain the Venus fallback, while unknown persisted products are rejected.
- **Polling**: Moved the Venus fast and medium command schedules out of the generic coordinator and into `VENUS_RUNTIME`.
- **Parsing**: Fixed-layout Venus responses now use declarative field sources; Venus-specific text responses remain product-local custom parsers.
- **State model**: The live Venus coordinator now stores nested `VenusData`. Temporary flat read/metadata aliases preserve compatibility during platform migration.
- **Tests**: Added isolated tests for runtime registration, parsing, field metadata, poll dispatch, product selection, compatibility behavior, and failure/boundary cases.
- **Declarative coverage tests**: Added direct tests for schema validation and failure paths, entity-plan topology and presence logic, and the declarative Jupiter runtime-summary, detailed-telemetry, event-history, repeated battery-pack, expansion, and derived-entity behavior.
- **Coverage**: Coverage includes every Python source file under `custom_components/marstek_ble` and `standalone_test` with no file-level exceptions.
- **Testing policy**: Added a dedicated testing-and-coverage OKF concept and updated `Agents.md` to prohibit coverage omissions and use uncovered statements and branches as test-design input rather than exclusion criteria.

## 2026-08-05

- **Architecture**: Added branch-only declarative packet, dataclass, entity-description, product-profile, repeated-record, and child-device scaffolding.
- **Products**: Added declarative Venus and Jupiter-C Plus definitions without connecting them to the integration runtime.
- **Expansions**: Added fixed-limit Jupiter battery-pack records, setup-time child-device planning, slot-based identifiers, runtime presence checks, and expansion-increase records.
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
