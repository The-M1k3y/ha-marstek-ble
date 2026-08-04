---
okf_version: "0.2"
---

# Marstek BLE knowledge

This bundle describes the repository at source revision `59ea1c3f0e6f239cecbae7f9024e0dc48c328d89`. It is organized for progressive disclosure: read the scope first, then open only the concepts relevant to the task.

# Scope

* [Knowledge scope](scope.md) - Defines the included products and sources, trust boundaries, and explicit exclusions.

# Codebase

* [Codebase overview](codebase-overview.md) - Purpose, supported discovery patterns, Home Assistant surfaces, and repository structure.
* [Runtime architecture](architecture.md) - Setup, polling, BLE connection management, parsing, state propagation, and current product-coupling points.

# Venus communication protocol

* [Venus BLE protocol](protocol/venus/) - Progressive entry point for transport, framing, command inventory, and individual message schemas.
* [Venus BLE transport and framing](venus-ble-protocol.md) - GATT service, frame structure, checksum, request/response correlation, and connection lifecycle.
* [Venus command summary](venus-command-reference.md) - Compact list of commands sent or parsed by the integration.

# Maintenance

* [Update log](log.md) - Chronological history of this bundle.
