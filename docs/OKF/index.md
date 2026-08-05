---
okf_version: "0.2"
---

# Marstek BLE knowledge

This bundle describes the existing Venus integration and branch-only
multi-product scaffolding at source revision
`17d3211e12989eb428681f5959707e9403e61bf6`. Read the scope first, then open only
the concepts relevant to the task.

# Scope

- [Knowledge scope](scope.md) - Included products, sanitized sources, trust boundaries, and explicit exclusions.

# Codebase and architecture

- [Codebase overview](codebase-overview.md) - Existing integration purpose, Home Assistant surfaces, and repository structure.
- [Runtime architecture](architecture.md) - Existing setup, polling, BLE lifecycle, parsing, state propagation, and product-coupling points.
- [Declarative product model](declarative-product-model.md) - Packet schemas, nested dataclasses, entity plans, repeated records, child devices, and expansion repairs.

# Product protocols

- [Venus BLE protocol](protocol/venus/) - Existing integration transport, commands, and message schemas.
- [Jupiter-C Plus BLE protocol](protocol/jupiter/) - Sanitized runtime, detailed telemetry, event history, and expansion topology.

# Maintenance

- [Update log](log.md) - Chronological history of this bundle.
