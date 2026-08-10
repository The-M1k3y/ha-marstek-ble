---
okf_version: "0.2"
---

# Marstek BLE knowledge

This bundle describes the runtime-enabled Venus and Jupiter product models, live declarative read-only entity infrastructure, and the repository's isolated testing and coverage policy at source revision `112abd322722b2e84bcdf34ee4b0325bf14b7313`. Read the scope first, then open only the concepts relevant to the task.

# Scope

- [Knowledge scope](scope.md) - Included products, runtime status, sanitized sources, trust boundaries, and explicit exclusions.

# Codebase and architecture

- [Codebase overview](codebase-overview.md) - Integration purpose, Home Assistant surfaces, runtime products, and repository layout.
- [Runtime architecture](architecture.md) - Product selection, polling, BLE lifecycle, parsing, live entities, and capability boundaries.
- [Declarative product model](declarative-product-model.md) - Packet schemas, nested dataclasses, runtimes, live entity plans, repeated records, and child devices.
- [Testing and coverage](testing-and-coverage.md) - Isolated test requirements, `known_issue` handling, full source coverage scope, and coverage-driven test design.

# Product protocols

- [Venus BLE protocol](protocol/venus/) - Runtime-enabled Venus transport, commands, and message schemas.
- [Jupiter-C Plus BLE protocol](protocol/jupiter/) - Runtime-enabled Jupiter telemetry, detailed packet schemas, live PV/battery entities, event history, and expansion topology.

# Maintenance

- [Update log](log.md) - Chronological history of this bundle.
