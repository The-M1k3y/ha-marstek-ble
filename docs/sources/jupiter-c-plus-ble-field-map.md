# Jupiter-C Plus BLE field map

This source records only sanitized protocol structure derived from approved,
redacted reverse-engineering results. It intentionally excludes complete frames,
payload hex, timestamps, device or cloud identifiers, MAC addresses, Wi-Fi
names, observed telemetry values, event contents, and capture-specific counters.

All offsets are relative to the first command-payload byte. Multi-byte values are
little-endian unless stated otherwise.

## Confidence terminology

- **Confirmed**: directly matched independent device or physical behaviour.
- **Strong**: consistently produced credible values or matched an independent
  implementation, but lacks a field-specific controlled test.
- **Tentative**: plausible structure or meaning that requires more validation.

## Packet inventory

| Command | Payload length | Status                         |
| ------- | -------------: | ------------------------------ |
| `0x03`  |             74 | Runtime summary                |
| `0x04`  |             97 | ASCII device information       |
| `0x08`  |       variable | ASCII Wi-Fi SSID               |
| `0x0D`  |             12 | Structure unresolved           |
| `0x13`  |            160 | Twenty 8-byte event records    |
| `0x14`  |            166 | Detailed inverter/MPPT/BMS     |
| `0x21`  |              1 | Meaning unresolved             |
| `0x22`  |              1 | Meaning unresolved             |
| `0x24`  |              1 | Meaning unresolved             |
| `0x1A`  |              — | No response structure observed |
| `0x1C`  |              — | No response structure observed |

## `0x03` runtime summary

| Offset | Length | Type          | Name                      | Unit / scale | Confidence |
| -----: | -----: | ------------- | ------------------------- | ------------ | ---------- |
| `0x00` |      2 | `u16 LE`      | PV input 1 power          | W            | Confirmed  |
| `0x02` |      1 | `u8 / bool`   | PV input 1 connected      | boolean      | Confirmed  |
| `0x03` |      2 | `u16 LE`      | PV input 2 power          | W            | Confirmed  |
| `0x05` |      1 | `u8 / bool`   | PV input 2 connected      | boolean      | Confirmed  |
| `0x06` |      2 | `u16 LE`      | PV input 3 power          | W            | Confirmed  |
| `0x08` |      1 | `u8 / bool`   | PV input 3 connected      | boolean      | Confirmed  |
| `0x09` |      2 | `u16 LE`      | PV input 4 power          | W            | Confirmed  |
| `0x0B` |      1 | `u8 / bool`   | PV input 4 connected      | boolean      | Confirmed  |
| `0x0C` |      2 | `u16 LE`      | AC/grid output power      | W            | Confirmed  |
| `0x0E` |      1 | `u8 / bool`   | AC/grid output active     | boolean      | Confirmed  |
| `0x0F` |      3 | unknown       | unknown                   | —            | —          |
| `0x12` |      1 | `u8 / bool`   | Battery charging active   | boolean      | Confirmed  |
| `0x13` |      2 | `u16 LE`      | Stored battery energy     | 10 Wh        | Confirmed  |
| `0x15` |      1 | `u8`          | Battery state of charge   | %            | Confirmed  |
| `0x16` |      1 | `u8`          | EMS firmware summary      | raw version  | Confirmed  |
| `0x17` |      4 | `u32 LE`      | Daily PV generation       | 0.01 kWh     | Strong     |
| `0x1B` |      4 | `u32 LE`      | Monthly PV generation     | 0.01 kWh     | Strong     |
| `0x1F` |      4 | `u32 LE`      | Total PV generation       | 0.01 kWh     | Confirmed  |
| `0x23` |      4 | unknown       | unknown                   | —            | —          |
| `0x27` |      4 | `u32 LE`      | Daily discharge energy    | 0.01 kWh     | Confirmed  |
| `0x2B` |      4 | `u32 LE`      | Monthly discharge energy  | 0.01 kWh     | Confirmed  |
| `0x2F` |      2 | `u16 LE`      | EMS firmware version      | raw version  | Confirmed  |
| `0x31` |      2 | `u16 LE`      | Inverter firmware version | raw version  | Confirmed  |
| `0x33` |      2 | `u16 LE`      | MPPT firmware version     | raw version  | Confirmed  |
| `0x35` |      2 | `u16 LE`      | BMS firmware version      | raw version  | Confirmed  |
| `0x37` |      5 | unknown       | unknown                   | —            | —          |
| `0x3C` |      1 | `u8 bitfield` | Operational status        | raw          | Tentative  |
| `0x3D` |     13 | unknown       | unknown                   | —            | —          |

## `0x04` device information

The payload is a comma-separated ASCII sequence of `key=value` entries.

| Key      | Field                     | Confidence |
| -------- | ------------------------- | ---------- |
| `type`   | Device type / model ID    | Confirmed  |
| `id`     | Cloud/device identifier   | Confirmed  |
| `mac`    | Bluetooth MAC address     | Confirmed  |
| `ems_v`  | EMS firmware version      | Confirmed  |
| `inv_v`  | Inverter firmware version | Confirmed  |
| `mppt_v` | MPPT firmware version     | Confirmed  |
| `bms_v`  | BMS firmware version      | Confirmed  |

Unknown keys should be ignored or preserved without failing the complete packet.

## `0x08` Wi-Fi SSID

The complete payload is an ASCII SSID. Its length is configuration-dependent.

## `0x0D` unresolved status

The payload is 12 bytes. No field interpretation is retained because the Venus
layout has not been validated for Jupiter.

## `0x13` event history

The packet contains exactly 20 fixed records of 8 bytes each.

| Relative offset | Length | Type     | Field               | Confidence |
| --------------: | -----: | -------- | ------------------- | ---------- |
|         `+0x00` |      2 | `u16 LE` | Year                | Strong     |
|         `+0x02` |      1 | `u8`     | Month               | Strong     |
|         `+0x03` |      1 | `u8`     | Day                 | Strong     |
|         `+0x04` |      1 | `u8`     | Hour                | Strong     |
|         `+0x05` |      1 | `u8`     | Minute              | Strong     |
|         `+0x06` |      1 | `u8`     | Event value or ID   | Tentative  |
|         `+0x07` |      1 | `u8`     | Event type or state | Tentative  |

The records form a circular history buffer. Event-value semantics are not stable
enough for named Home Assistant events or entities.

## `0x14` detailed telemetry

| Offset | Length | Type           | Name                                     | Unit / scale | Confidence |
| -----: | -----: | -------------- | ---------------------------------------- | ------------ | ---------- |
| `0x00` |      2 | `u16 bitfield` | Inverter operating-state flags           | raw          | Strong     |
| `0x02` |      2 | `u16 LE`       | Inverter error code                      | raw          | Strong     |
| `0x04` |      2 | `u16 LE`       | Inverter warning code                    | raw          | Strong     |
| `0x06` |      2 | `u16 LE`       | Grid voltage                             | 0.1 V        | Strong     |
| `0x08` |      2 | `u16 LE`       | Grid current                             | 0.1 A        | Strong     |
| `0x0A` |      2 | `u16 LE`       | Grid power factor                        | raw          | Strong     |
| `0x0C` |      2 | `u16 LE`       | Grid frequency                           | 0.01 Hz      | Confirmed  |
| `0x0E` |      2 | `u16 LE`       | Internal DC/bus voltage                  | 0.1 V        | Strong     |
| `0x10` |      2 | `i16 LE`       | AC/grid output power                     | W            | Confirmed  |
| `0x12` |      2 | `i16 LE`       | Inverter temperature                     | °C           | Strong     |
| `0x14` |      4 | `u32 LE`       | Daily discharge energy                   | 0.01 kWh     | Confirmed  |
| `0x18` |      4 | `u32 LE`       | Local cumulative discharge counter       | 0.01 kWh     | Strong     |
| `0x1C` |      4 | `u32 LE`       | Monthly discharge energy                 | 0.01 kWh     | Confirmed  |
| `0x20` |      2 | `u16 bitfield` | MPPT controller/input-active flags       | raw          | Confirmed* |
| `0x22` |      2 | `u16 LE`       | MPPT error code                          | raw          | Strong     |
| `0x24` |      2 | `i16 LE`       | MPPT temperature                         | °C           | Strong     |
| `0x26` |      2 | `u16 LE`       | MPPT warning code                        | raw          | Strong     |
| `0x28` |      2 | `u16 LE`       | PV input 1 voltage                       | 0.1 V        | Confirmed  |
| `0x2A` |      2 | `u16 LE`       | PV input 1 current                       | 0.1 A        | Confirmed  |
| `0x2C` |      2 | `u16 LE`       | PV input 1 power                         | 0.1 W        | Confirmed  |
| `0x2E` |      2 | `u16 LE`       | PV input 2 voltage                       | 0.1 V        | Confirmed  |
| `0x30` |      2 | `u16 LE`       | PV input 2 current                       | 0.1 A        | Confirmed  |
| `0x32` |      2 | `u16 LE`       | PV input 2 power                         | 0.1 W        | Confirmed  |
| `0x34` |      2 | `u16 LE`       | PV input 3 voltage                       | 0.1 V        | Confirmed  |
| `0x36` |      2 | `u16 LE`       | PV input 3 current                       | 0.1 A        | Confirmed  |
| `0x38` |      2 | `u16 LE`       | PV input 3 power                         | 0.1 W        | Confirmed  |
| `0x3A` |      2 | `u16 LE`       | PV input 4 voltage                       | 0.1 V        | Confirmed  |
| `0x3C` |      2 | `u16 LE`       | PV input 4 current                       | 0.1 A        | Confirmed  |
| `0x3E` |      2 | `u16 LE`       | PV input 4 power                         | 0.1 W        | Confirmed  |
| `0x40` |      4 | `u32 LE`       | Daily PV generation                      | 0.01 kWh     | Strong     |
| `0x44` |      4 | unknown        | unknown                                  | —            | —          |
| `0x48` |      4 | `u32 LE`       | Monthly PV generation                    | 0.01 kWh     | Strong     |
| `0x4C` |      4 | `u32 LE`       | Total PV generation                      | 0.01 kWh     | Confirmed  |
| `0x50` |      2 | `u16 LE`       | MPPT DC output voltage                   | 0.1 V        | Strong     |
| `0x52` |      2 | `i16 LE`       | MPPT DC output current                   | 0.1 A        | Strong     |
| `0x54` |      2 | `u16 LE`       | Base voltage                             | 0.1 V        | Tentative  |
| `0x56` |      2 | `u16 LE`       | PE voltage                               | 0.1 V        | Tentative  |
| `0x58` |      2 | `u16 LE`       | Charge-voltage limit                     | 0.1 V        | Strong     |
| `0x5A` |      2 | `u16 LE`       | Dynamic charge-current limit             | 0.1 A        | Confirmed  |
| `0x5C` |      2 | `u16 LE`       | Discharge-current limit                  | 0.1 A        | Strong     |
| `0x5E` |      2 | `u16 LE`       | Battery state of charge                  | %            | Confirmed  |
| `0x60` |      2 | `u16 LE`       | Battery state of health                  | %            | Strong     |
| `0x62` |      2 | `u16 LE`       | Rated battery capacity                   | Wh           | Confirmed  |
| `0x64` |      2 | `u16 LE`       | BMS firmware version                     | raw version  | Confirmed  |
| `0x66` |      2 | `u16 LE`       | Battery voltage                          | 0.01 V       | Confirmed  |
| `0x68` |      2 | `i16 LE`       | Battery current; positive means charging | 0.1 A        | Confirmed  |
| `0x6A` |      2 | `i16 LE`       | Battery temperature                      | 0.1 °C       | Strong     |
| `0x6C` |      2 | `u16 LE`       | BMS error code 1                         | raw          | Strong     |
| `0x6E` |      2 | `u16 LE`       | BMS warning code 1                       | raw          | Strong     |
| `0x70` |      2 | `u16 LE`       | BMS error code 2                         | raw          | Strong     |
| `0x72` |      2 | `u16 LE`       | BMS warning code 2                       | raw          | Strong     |
| `0x74` |      1 | `u8 bitfield`  | Cell flags                               | raw          | Strong     |
| `0x75` |      1 | `u8 bitfield`  | BMS status flags                         | raw          | Strong     |
| `0x76` |      2 | `u16 LE`       | Populated battery-pack record count      | count        | Strong     |
| `0x78` |      2 | `u16 LE`       | Stored battery energy                    | Wh           | Confirmed  |
| `0x7A` |     32 | repeated       | Four 8-byte battery-pack summary records | —            | Strong     |
| `0x9A` |      2 | `i16 LE`       | Battery temperature sensor 1             | °C           | Strong     |
| `0x9C` |      2 | `i16 LE`       | Battery temperature sensor 2             | °C           | Strong     |
| `0x9E` |      2 | `i16 LE`       | Battery temperature sensor 3             | °C           | Strong     |
| `0xA0` |      2 | `i16 LE`       | Battery temperature sensor 4             | °C           | Strong     |
| `0xA2` |      2 | `i16 LE`       | BMS/environment temperature              | °C           | Strong     |
| `0xA4` |      2 | `i16 LE`       | BMS MOSFET temperature                   | °C           | Strong     |

`*` MPPT bits 4–7 identify active PV inputs 1–4. Bit 2 is strongly
supported as an initialized/ready state. Other bits remain unresolved.

### Battery-pack summary record

The records begin at offsets `0x7A`, `0x82`, `0x8A`, and `0x92`. Index 0 is the
base battery; indices 1–3 are expansion positions.

| Relative offset | Length | Type     | Field                      | Unit       | Confidence |
| --------------: | -----: | -------- | -------------------------- | ---------- | ---------- |
|         `+0x00` |      1 | `u8`     | Highest-voltage cell index | zero-based | Strong     |
|         `+0x01` |      1 | `u8`     | Lowest-voltage cell index  | zero-based | Strong     |
|         `+0x02` |      2 | `u16 LE` | Highest cell voltage       | mV         | Strong     |
|         `+0x04` |      2 | `u16 LE` | Lowest cell voltage        | mV         | Strong     |
|         `+0x06` |      2 | `u16 LE` | Pack status or fault word  | raw        | Tentative  |

## `0x21`, `0x22`, and `0x24`

Each response is one raw byte. Venus meanings for these commands are not applied
without Jupiter-specific validation.

## Commands without a response schema

Commands `0x1A` and `0x1C` were requested but no response structure was
available. No Jupiter schema is defined for either command.
