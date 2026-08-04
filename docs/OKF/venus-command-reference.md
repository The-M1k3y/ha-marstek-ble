---
type: Protocol Command Reference
title: Venus command summary
description: Compact inventory of BLE commands sent or parsed by the integration, linking to focused message schemas.
tags: [venus, protocol, commands, payloads]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T10:05:00Z }
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
---

# Detailed schemas

Start with the [Venus message inventory](protocol/venus/messages/). Each message concept documents request and response payloads, used fields, unknown ranges, offsets, lengths, types, names, units, and implementation caveats.

# Command inventory

| Command | Message or use                          | Detailed concept                                                                 |
| ------: | --------------------------------------- | -------------------------------------------------------------------------------- |
| `0x03`  | Runtime information                     | [Telemetry](protocol/venus/messages/telemetry/03-runtime-information.md)          |
| `0x04`  | Device information                      | [Telemetry](protocol/venus/messages/telemetry/04-device-information.md)           |
| `0x05`  | EPS mode                                | [Control](protocol/venus/messages/control/05-eps-mode.md)                         |
| `0x06`  | AC input                                | [Control](protocol/venus/messages/control/06-ac-input.md)                         |
| `0x07`  | Generator                               | [Control](protocol/venus/messages/control/07-generator.md)                        |
| `0x08`  | Wi-Fi SSID                              | [Telemetry](protocol/venus/messages/telemetry/08-wifi-ssid.md)                    |
| `0x09`  | Buzzer / manual operating mode          | [Control](protocol/venus/messages/control/09-buzzer-manual-mode.md)               |
| `0x0D`  | System-data query / charge-mode write   | [Telemetry](protocol/venus/messages/telemetry/0d-system-data.md), [control](protocol/venus/messages/control/0d-charge-mode.md) |
| `0x0E`  | Output 1 / self-consumption mode        | [Control](protocol/venus/messages/control/0e-output-self-consumption.md)          |
| `0x13`  | Timer information                       | [Telemetry](protocol/venus/messages/telemetry/13-timer-information.md)            |
| `0x14`  | BMS data                                | [Telemetry](protocol/venus/messages/telemetry/14-bms-data.md)                     |
| `0x15`  | Power mode                              | [Control](protocol/venus/messages/control/15-power-mode.md)                       |
| `0x16`  | AC power                                | [Control](protocol/venus/messages/control/16-ac-power.md)                         |
| `0x17`  | Total power                             | [Control](protocol/venus/messages/control/17-total-power.md)                      |
| `0x1A`  | Configuration data                      | [Telemetry](protocol/venus/messages/telemetry/1a-configuration-data.md)           |
| `0x1C`  | Logs                                    | [Telemetry](protocol/venus/messages/telemetry/1c-logs.md)                         |
| `0x20`  | CT polling-rate write                   | [Control](protocol/venus/messages/control/20-ct-polling-rate-write.md)            |
| `0x21`  | Meter IP                                | [Telemetry](protocol/venus/messages/telemetry/21-meter-ip.md)                     |
| `0x22`  | CT polling-rate readback                | [Telemetry](protocol/venus/messages/telemetry/22-ct-polling-rate.md)              |
| `0x24`  | Network information                     | [Telemetry](protocol/venus/messages/telemetry/24-network-information.md)          |
| `0x25`  | Reboot                                  | [Control](protocol/venus/messages/control/25-reboot.md)                           |
| `0x28`  | Local API status parser                 | [Telemetry](protocol/venus/messages/telemetry/28-local-api-status.md)             |

`0x0A` remains defined as `CMD_AI_MODE`, but the current code neither sends it nor parses it; it is therefore not documented as an active message type.
