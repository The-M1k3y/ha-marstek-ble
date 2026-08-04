# Marstek BLE OKF update log

## 2026-08-04

* **Update**: Added a progressive `protocol/venus/messages/` hierarchy with one focused concept for every BLE message sent or parsed by the integration.
* **Update**: Documented request and response fields by byte offset, including length, type, name, unit, descriptions, unknown gaps, ignored suffixes, and overlapping interpretations.
* **Update**: Refactored the command reference into a compact inventory linking to the detailed message concepts.
* **Update**: Required aligned Markdown tables and byte-offset ordering in `Agents.md`.
* **Initialization**: Created the OKF v0.2 knowledge bundle from repository revision `59ea1c3f0e6f239cecbae7f9024e0dc48c328d89`.
* **Creation**: Added codebase, architecture, Venus BLE transport, and Venus command/payload references.
* **Scope**: Explicitly excluded Jupiter-C reverse-engineering material and any information not present in the repository sources.
