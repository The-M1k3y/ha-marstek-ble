---
type: Protocol Command Reference
title: Venus command and payload reference
description: Command identifiers, control payloads, and response fields implemented for Venus units.
tags: [venus, protocol, commands, payloads, bms]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T09:37:02Z }
sources:
  - id: constants
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/const.py
    title: Command constants
  - id: device
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/marstek_device.py
    title: Payload parsers and command transport
  - id: coordinator
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/coordinator.py
    title: Poll command schedule
  - id: switches
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/switch.py
    title: Switch control payloads
  - id: selects
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/select.py
    title: Select control payloads
  - id: buttons
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/button.py
    title: Button control payloads
---

# Reading this reference

Offsets are relative to the response payload, not the complete BLE frame. Integer types are little-endian. Names and units describe the repository's current interpretation and are not vendor-confirmed. A field absent from a shorter payload retains its previous value in `MarstekData`.

# Command inventory

| Command | Repository name or use | Current behavior |
|---:|---|---|
| `0x03` | Runtime information | Fast-polled and parsed |
| `0x04` | Device information | Medium-polled and parsed |
| `0x05` | EPS mode | Switch control, payload `00`/`01` |
| `0x06` | AC input | Switch control, payload `00`/`01` |
| `0x07` | Generator | Switch control, payload `00`/`01` |
| `0x08` | Wi-Fi SSID | Medium-polled and parsed |
| `0x09` | Buzzer / manual work mode | Dual-use switch and operating-mode control |
| `0x0A` | AI mode constant | Constant remains, but the operating-mode entity explicitly marks AI mode unsupported over BLE and does not send it |
| `0x0D` | System data / charge mode | Dual-use read parser and select control |
| `0x0E` | Output control / self-consumption mode | Dual-use switch and operating-mode control |
| `0x13` | Timer information | Medium-polled and parsed |
| `0x14` | BMS data | Fast-polled and parsed |
| `0x15` | Power mode | Fixed-value button controls |
| `0x16` | AC power | Fixed-value button control |
| `0x17` | Total power | Fixed-value button control |
| `0x1A` | Configuration data | Medium-polled and parsed |
| `0x1C` | Logs | Medium-polled; no payload parser is registered |
| `0x20` | CT polling-rate write | Select control |
| `0x21` | Meter IP | Medium-polled with request payload `0B`; parsed |
| `0x22` | CT polling-rate read | Medium-polled and parsed |
| `0x24` | Network information | Medium-polled and parsed |
| `0x25` | Reboot | Button control with empty payload |
| `0x28` | Local API status | Parser exists, but the current coordinator poll schedule does not request it |

The same command byte may mean different things for an empty/read request and a write payload. Preserve this distinction when refactoring the protocol.[^constants][^coordinator]

# Control payloads

## Boolean controls

The switch platform sends one byte: `01` for on and `00` for off.[^switches]

| Command | Entity |
|---:|---|
| `0x0E` | Output 1 control |
| `0x05` | EPS mode |
| `0x06` | AC input |
| `0x07` | Generator |
| `0x09` | Buzzer |

Only Output 1 has a parsed status source (`out1_active`). The other switches use assumed state after a successful matching response.[^switches]

## Operating mode

| Option | Command | Payload |
|---|---:|---:|
| Self-Consumption | `0x0E` | `01` |
| Manual | `0x09` | `01` |

The operating-mode entity does not derive its current value from coordinator data; it remembers a selection made during the current entity lifetime. AI Optimization is explicitly excluded by the current entity because it is not supported over BLE.[^selects]

## Charge mode

All charge-mode writes use command `0x0D`.[^selects]

| Option | Payload | Value used to map readback `config_mode` |
|---|---:|---:|
| PV2 Passthrough | `00` | `0` |
| Load First | `01` | `1` |
| Simultaneous Charge Discharge | `02` | `2` |

## CT polling rate

Writes use command `0x20`; readback comes from command `0x22`.[^selects]

| Option | Payload/readback value |
|---|---:|
| Fastest | `0` |
| Medium | `1` |
| Slowest | `2` |

## Fixed power and reboot buttons

| Entity | Command | Payload | Payload interpretation in source |
|---|---:|---:|---|
| Reboot | `0x25` | empty | none |
| Set 800 W Mode | `0x15` | `20 03` | little-endian `800` |
| Set 2500 W Mode | `0x15` | `C4 09` | little-endian `2500` |
| Set AC Power 2500 W | `0x16` | `C4 09` | little-endian `2500` |
| Set Total Power 2500 W | `0x17` | `C4 09` | little-endian `2500` |

[^buttons]

# Parsed response schemas

## `0x03` runtime information

The parser requires at least 37 payload bytes. Payloads shorter than 60 bytes enter a limited “short” branch whose offsets are explicitly described in source comments as tentative.[^device]

### Baseline fields

| Offset | Type | Field | Conversion/meaning |
|---:|---|---|---|
| `0x0F` | `u8` bitfield | `wifi_connected` | bit 0 |
| `0x0F` | `u8` bitfield | `mqtt_connected` | bit 1 |
| `0x10` | `u8` | `out1_active` | nonzero = true |
| `0x14` | `u16` | `out1_power` | W |
| `0x1C` | `u8` | `extern1_connected` | nonzero = true |
| `0x21` | `s16` | `temp_low` | divide by 10 °C; long branch only |
| `0x23` | `s16` | `temp_high` | divide by 10 °C; long branch only |

### Additional fields for payload length at least 100

| Offset | Type | Field | Conversion/meaning |
|---:|---|---|---|
| `0x00` | `s16` | `grid_power` | W |
| `0x02` | `s16` | `solar_power` | W |
| `0x04` | `u8` | `work_mode` | raw integer |
| `0x0C` | `u16` | `product_code` | raw integer |
| `0x0E` | `u32` | `daily_energy_charged` | divide by 100 kWh |
| `0x12` | `u32` | `monthly_energy_charged` | divide by 1000 kWh |
| `0x16` | `u32` | `daily_energy_discharged` | divide by 100 kWh |
| `0x1A` | `u32` | `monthly_energy_discharged` | divide by 100 kWh |
| `0x29` | `u32` | `total_energy_charged` | divide by 100 kWh |
| `0x2D` | `u32` | `total_energy_discharged` | divide by 100 kWh |
| `0x4A` | `u16` | `power_rating` | W |

The additional interpretation overlaps bytes used by some baseline fields—for example the four-byte monthly charge value includes the two bytes read as `out1_power`, and the daily charge value includes the status byte at `0x0F`. This reference preserves the code as written; it does not assert that every overlapping interpretation is simultaneously valid for every Venus firmware.[^device]

## `0x04` device information

ASCII text containing comma-separated `key=value` pairs.[^device]

| Input key | Destination field |
|---|---|
| `type` | `device_type` |
| `id` | `device_id` |
| `sn` | `serial_number` |
| `mac` | `mac_address` |
| `dev_ver`, `fc_ver`, or `fw` | `firmware_version` |
| `hw` | `hardware_version` |

Unknown keys are ignored.

## `0x08` Wi-Fi SSID

The entire payload is decoded as ASCII with undecodable bytes ignored, then surrounding whitespace is stripped.[^device]

## `0x0D` system data

Minimum length: 11 bytes.[^device]

| Offset | Type | Field |
|---:|---|---|
| `0x00` | `u8` | `system_status` |
| `0x01` | `u16` | `system_value_1` |
| `0x03` | `u16` | `system_value_2` |
| `0x05` | `u16` | `system_value_3` |
| `0x07` | `u16` | `system_value_4` |
| `0x09` | `u16` | `system_value_5` |

The five value fields remain intentionally generic in the current data model.

## `0x13` timer information

Minimum length: 45 bytes.[^device]

| Offset | Type | Field | Conversion |
|---:|---|---|---|
| `0x00` | `u8` | `adaptive_mode_enabled` | nonzero = true |
| `0x25` | `u8` | `smart_meter_connected` | nonzero = true |
| `0x26` | `u16` | `adaptive_power_out` | W |

## `0x14` BMS data

Minimum length: 80 bytes.[^device]

| Offset | Type | Field | Conversion/meaning |
|---:|---|---|---|
| `0x00` | `u16` | `bms_version` | raw integer |
| `0x02` | `u16` | `voltage_limit` | divide by 10 V |
| `0x04` | `u16` | `charge_current_limit` | divide by 10 A |
| `0x06` | `s16` | `discharge_current_limit` | divide by 10 A |
| `0x08` | `u16` | `battery_soc` | percent as exposed |
| `0x0A` | `u16` | `battery_soh` | percent as exposed |
| `0x0C` | `u16` | `design_capacity` | Wh as exposed |
| `0x0E` | `u16` | `battery_voltage` | divide by 100 V |
| `0x10` | `s16` | `battery_current` | divide by 10 A |
| `0x12` | `u16` | `battery_temp` | °C as exposed; no scale applied |
| `0x1A` | `u16` | `error_code` | raw integer |
| `0x1C` | `u32` | `warning_code` | raw integer/bitfield |
| `0x20` | `u32` | `runtime_hours` | milliseconds divided by 3,600,000 |
| `0x26` | `u16` | `mosfet_temp` | °C as exposed; no scale applied |
| `0x28` | `u16` | `temp_sensor_1` | °C as exposed; no scale applied |
| `0x2A` | `u16` | `temp_sensor_2` | °C as exposed; no scale applied |
| `0x2C` | `u16` | `temp_sensor_3` | °C as exposed; no scale applied |
| `0x2E` | `u16` | `temp_sensor_4` | °C as exposed; no scale applied |
| `0x30 + 2n` | `u16` | `cell_voltages[n]`, `n=0..15` | divide by 1000 V |

## `0x1A` configuration data

Minimum length: 17 bytes.[^device]

| Offset | Type | Field |
|---:|---|---|
| `0x00` | `u8` | `config_mode` |
| `0x04` | `s8` | `config_status` |
| `0x10` | `u8` | `config_value` |

## `0x21` meter IP

If every payload byte is `FF`, the data model stores the literal string `(not set)`. Otherwise, the payload is decoded as ASCII and NUL bytes are stripped from both ends.[^device]

## `0x22` CT polling rate

The first payload byte is stored as an unsigned integer.[^device]

## `0x24` network information

ASCII text in the form:

```text
ip:192.0.2.10,gate:192.0.2.1,mask:255.255.255.0,dns:192.0.2.1
```

The full string is retained. Recognized keys populate `ip_address`, `gateway`, `subnet_mask`, and `dns_server`; both `gate` and `gateway` are accepted.[^device]

## `0x28` local API status

Minimum length: 3 bytes.[^device]

| Offset | Type | Meaning |
|---:|---|---|
| `0x00` | `u8` | `1` = enabled; any other value = disabled |
| `0x01` | `u16` | port |

The stored representation is the string `enabled/<port>` or `disabled/<port>`.

[^constants]: Command constants.
[^device]: Payload parsers and command transport.
[^coordinator]: Poll command schedule.
[^switches]: Switch control payloads.
[^selects]: Select control payloads.
[^buttons]: Button control payloads.
