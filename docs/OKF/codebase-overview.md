---
type: Codebase Overview
title: ha-marstek-ble codebase overview
description: Purpose, supported discovery patterns, Home Assistant surfaces, and repository layout.
tags: [home-assistant, bluetooth, integration, architecture, venus]
status: draft
source_revision: "59ea1c3f0e6f239cecbae7f9024e0dc48c328d89"
generated: { by: openai/gpt-5.6-thinking, at: 2026-08-04T09:37:02Z }
sources:
  - id: readme
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/README.md
    title: Repository README
  - id: manifest
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/manifest.json
    title: Integration manifest
  - id: init
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/__init__.py
    title: Integration setup and unload module
  - id: config-flow
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/config_flow.py
    title: Configuration and discovery flow
  - id: sensors
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/sensor.py
    title: Sensor platform
  - id: binary-sensors
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/binary_sensor.py
    title: Binary sensor platform
  - id: switches
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/switch.py
    title: Switch platform
  - id: selects
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/select.py
    title: Select platform
  - id: buttons
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/59ea1c3f0e6f239cecbae7f9024e0dc48c328d89/custom_components/marstek_ble/button.py
    title: Button platform
---

# Purpose

`ha-marstek-ble` is a Home Assistant custom integration for local Bluetooth Low Energy communication with Marstek Venus E energy-storage units. The repository labels the release beta/experimental and exposes monitoring, control, energy counters, BLE-proxy compatibility, and configurable polling without requiring cloud connectivity.[^readme]

The integration domain is `marstek_ble`, its integration type is `device`, and its Home Assistant IoT class is `local_polling`.[^manifest]

# Supported discovery surface

The manifest and config flow accept Bluetooth devices whose local names begin with:

| Prefix | Repository description |
|---|---|
| `MST_ACCP_` | Venus E hardware v2; described as tested |
| `MST_VNSE3_` | Venus E hardware v3; described as untested |

Each configured device receives its own config entry and coordinator. The config flow uses the Bluetooth address as the Home Assistant unique ID while also preventing a second entry with the same advertised name, which is intended to reduce duplicates when a device uses changing addresses.[^config-flow]

# Home Assistant platforms

`async_setup_entry` forwards one config entry to five platforms: sensor, binary sensor, button, switch, and select.[^init]

| Platform | Main responsibilities |
|---|---|
| `sensor.py` | Battery/BMS measurements, power and energy values, capacities, temperatures, 16 cell voltages, identity, networking, and diagnostic values |
| `binary_sensor.py` | Wi-Fi, MQTT, output, external-input, and smart-meter status |
| `switch.py` | Output, EPS, AC-input, generator, and buzzer commands |
| `select.py` | Operating mode, charge mode, and CT polling-rate selection |
| `button.py` | Reboot and fixed power-setting commands |

The setup path always registers the Home Assistant device as manufacturer `Marstek` and model `Venus E`.[^init] Entity `device_info` blocks repeat the same fixed model designation across the platform modules.[^sensors][^binary-sensors][^switches][^selects][^buttons]

# Data surfaces

The central `MarstekData` snapshot is projected into entities. Important groups include:

- battery voltage, current, state of charge, state of health, temperature, limits, runtime, errors, warnings, and 16 cell voltages;
- computed battery power, charging power, discharging power, remaining capacity, and available capacity;
- output, grid, solar, daily/monthly/total energy, and temperature measurements;
- device identity, firmware/hardware version, Wi-Fi and network configuration; and
- operating/configuration diagnostics and connectivity flags.

Derived battery power uses voltage multiplied by current. Battery state is reported as charging above `+5 W`, discharging below `-5 W`, and inactive between those thresholds.[^sensors]

# Repository structure

| Path | Role |
|---|---|
| `README.md` | User-facing installation, support, entity, and development overview |
| `custom_components/marstek_ble/manifest.json` | Home Assistant metadata, Bluetooth matchers, dependencies, and version |
| `custom_components/marstek_ble/__init__.py` | Config-entry setup, coordinator construction, device registration, platform forwarding, and unload |
| `custom_components/marstek_ble/config_flow.py` | Bluetooth discovery, manual selection, duplicate prevention, and polling options |
| `custom_components/marstek_ble/const.py` | Domain, UUIDs, discovery prefixes, intervals, backoff levels, and command identifiers |
| `custom_components/marstek_ble/coordinator.py` | Poll scheduling, availability handling, command sequencing, notification dispatch, and backoff |
| `custom_components/marstek_ble/marstek_device.py` | Data model, frame builder, notification parser, payload decoders, BLE client, response waits, and diagnostics history |
| `custom_components/marstek_ble/sensor.py` | Numeric and text sensors plus stale-data handling |
| `custom_components/marstek_ble/binary_sensor.py` | Boolean status entities |
| `custom_components/marstek_ble/switch.py` | Boolean control entities |
| `custom_components/marstek_ble/select.py` | Enumerated control entities |
| `custom_components/marstek_ble/button.py` | Stateless command entities |
| `custom_components/marstek_ble/diagnostics.py` | Redacted Home Assistant diagnostics export |

# Configuration

The options flow exposes two intervals:

- fast polling: `1–60 s`, default `1 s`;
- medium polling: `5–300 s`, default `60 s`, and never allowed below the fast interval.

The medium cadence is represented as an integer number of fast cycles, rounded upward by the coordinator.[^config-flow]

[^readme]: Repository README.
[^manifest]: Integration manifest.
[^init]: Integration setup and unload module.
[^config-flow]: Configuration and discovery flow.
[^sensors]: Sensor platform.
[^binary-sensors]: Binary sensor platform.
[^switches]: Switch platform.
[^selects]: Select platform.
[^buttons]: Button platform.
