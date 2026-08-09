---
okf_version: "0.2"
---

# Marstek BLE knowledge

This bundle describes the runtime-enabled Venus and Jupiter product models, the declarative multi-product scaffolding, and the repository's isolated testing and complete coverage policy at source revision `382dc8ce426b44fbe59ef23ae50487e62774bcef`. Read the scope first, then open only the concepts relevant to the task.

# Scope

- [Knowledge scope](scope.md) - Included products, runtime status, sanitized sources, trust boundaries, and explicit exclusions.

# Codebase and architecture

- [Codebase overview](codebase-overview.md) - Integration purpose, Home Assistant surfaces, product runtime structure, and repository layout.
- [Runtime architecture](architecture.md) - Product selection, polling, BLE lifecycle, runtime parsing, state propagation, and remaining migration boundaries.
- [Declarative product model](declarative-product-model.md) - Packet schemas, nested dataclasses, runtime adapters, entity plans, repeated records, child devices, and expansion repairs.
- [Testing and coverage](testing-and-coverage.md) - Isolated test requirements, `known_issue` handling, full source coverage scope, and coverage-driven test design.

# Product protocols

- [Venus BLE protocol](protocol/venus/) - Runtime-enabled Venus transport, commands, and message schemas.
- [Jupiter-C Plus BLE protocol](protocol/jupiter/) - Runtime-enabled Jupiter telemetry, detailed packet schemas, event history, and expansion topology.

# Maintenance

- [Update log](log.md) - Chronological history of this bundle.
