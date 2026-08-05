---
type: Device Topology
title: Jupiter-C Plus battery expansions
description: Fixed-limit battery records, child-device identity, entity creation, runtime presence, and expansion-change repairs.
tags: [jupiter, battery, expansion, child-device, repairs]
status: draft
source_revision: "17d3211e12989eb428681f5959707e9403e61bf6"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-05T14:19:00Z }
sources:
  - id: model
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/products/jupiter.py
    title: Jupiter battery child-device specification
  - id: entities
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/17d3211e12989eb428681f5959707e9403e61bf6/custom_components/marstek_ble/entity.py
    title: Repeated entity planning and expansion-change detection
  - id: sanitized-map
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/2cd631c99cf445d0526f450e1f7d5e55f5958178/docs/sources/jupiter-c-plus-ble-field-map.md
    title: Sanitized Jupiter field map
---

# Packet topology

Detailed telemetry contains a populated-pack count followed by four fixed 8-byte
summary records:

| Index | Role                 | Payload offset |
| ----: | -------------------- | -------------: |
|     0 | Base battery         |         `0x7A` |
|     1 | Expansion position 1 |         `0x82` |
|     2 | Expansion position 2 |         `0x8A` |
|     3 | Expansion position 3 |         `0x92` |

The in-memory list always contains four `JupiterBatteryPackData` instances. The
reported count controls which records are present and which child devices are
included in the setup-time entity plan.

# Entity and device creation

The plan is built during setup, reload, or explicit reconfiguration. It creates
the base battery and only the expansion positions reported as populated. Unused
positions do not create empty Home Assistant devices or entities.

Each configured child exposes the same entity set:

- highest-voltage cell index;
- lowest-voltage cell index;
- highest cell voltage;
- lowest cell voltage; and
- raw status or fault word.

# Stable identifiers

Child identifiers are slot-based and scoped below the main device:

```text
<main identifier>:battery_pack:0
<main identifier>:battery_pack:1
<main identifier>:battery_pack:2
<main identifier>:battery_pack:3
```

This identifies the position rather than a particular physical battery. A future
serial number may be exposed as telemetry without changing these identifiers.
Changing registry identifiers later would require an explicit migration.

# Runtime changes and future repairs

Every repeated child binding retains a presence condition. A decrease in the
reported count can therefore make an already configured child unavailable
without shifting another child's identity.

`ProductProfile.detect_expansion_increases()` compares current telemetry with the
startup plan. If the count increases, it returns an `ExpansionChange` with a
stable issue ID and translation key. A future integration adapter can create a
warning repair asking the user to reload or reconfigure the entry. Newly found
children are created when the plan is rebuilt; the scaffolding does not modify
the running entity set automatically.
