---
type: Device Topology
title: Jupiter-C Plus battery expansions
description: Fixed-limit battery records, child-device identity, live entity creation, and runtime presence.
tags: [jupiter, battery, expansion, child-device]
status: draft
source_revision: "4a91e24a21a63171cfbffad4111b8caf5d25432c"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-10T11:57:00Z }
sources:
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/4a91e24a21a63171cfbffad4111b8caf5d25432c/custom_components/marstek_ble/products/jupiter.py
    title: Jupiter battery child-device specification
  - id: entities
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/entity.py
    title: Repeated entity planning and presence bindings
  - id: entity-runtime
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/112abd322722b2e84bcdf34ee4b0325bf14b7313/custom_components/marstek_ble/product_entity_platform.py
    title: Live repeated-entity synchronization
---

# Packet topology

Detailed telemetry contains a populated-pack count followed by four fixed 8-byte summary records:

| Index | Role                 | Payload offset |
| ----: | -------------------- | -------------: |
|     0 | Base battery         |         `0x7A` |
|     1 | Expansion position 1 |         `0x82` |
|     2 | Expansion position 2 |         `0x8A` |
|     3 | Expansion position 3 |         `0x92` |

The in-memory list always contains four `JupiterBatteryPackData` instances. `pack_count` determines which positions are currently present.

# Live entity creation

The sensor platform creates child entities only for populated positions. Each child exposes the following diagnostic sensors while the record interpretation remains unverified:

- highest-voltage cell index;
- lowest-voltage cell index;
- highest cell voltage;
- lowest cell voltage; and
- raw status or fault word.

`ProductEntityManager` rebuilds the declarative plan on coordinator updates and adds only previously unseen keys. If `pack_count` grows from two to three, only position 2 is added. No empty devices are created for unpopulated positions.

# Stable identifiers

Child identifiers are slot-based and scoped below the main device:

```text
<main identifier>:battery_pack:0
<main identifier>:battery_pack:1
<main identifier>:battery_pack:2
<main identifier>:battery_pack:3
```

This identifies the physical position, not a specific battery serial number. A serial number could later be exposed as telemetry without changing registry identity.

# Runtime decreases

Every repeated child binding retains a presence condition. If `pack_count` decreases, previously created entities for higher positions remain registered but become unavailable. Other batteries do not shift identities.

`ProductProfile.detect_expansion_increases()` remains available for future repair or notification UX, but runtime entity creation itself now handles newly populated positions without requiring a reload.
