---
okf_version: "0.2"
---

# Marstek BLE knowledge

This bundle describes the runtime-enabled Venus product model and the still-declarative Jupiter multi-product scaffolding at source revision `48ab5b3f326ae34430af3a92b7e077c0a1b38772`. Read the scope first, then open only the concepts relevant to the task.

# Scope

- [Knowledge scope](scope.md) - Included products, runtime status, sanitized sources, trust boundaries, and explicit exclusions.

# Codebase and architecture

- [Codebase overview](codebase-overview.md) - Integration purpose, Home Assistant surfaces, product runtime structure, and repository layout.
- [Runtime architecture](architecture.md) - Product selection, polling, BLE lifecycle, runtime parsing, state propagation, and remaining migration boundaries.
- [Declarative product model](declarative-product-model.md) - Packet schemas, nested dataclasses, runtime adapters, entity plans, repeated records, child devices, and expansion repairs.

# Product protocols

- [Venus BLE protocol](protocol/venus/) - Runtime-enabled Venus transport, commands, and message schemas.
- [Jupiter-C Plus BLE protocol](protocol/jupiter/) - Sanitized declarative runtime, detailed telemetry, event history, and expansion topology; not yet integration-runtime enabled.

# Maintenance

- [Update log](log.md) - Chronological history of this bundle.
