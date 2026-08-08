"""Additional defensive-path tests for the retained legacy parser."""

from __future__ import annotations

from custom_components.marstek_ble.marstek_device import MarstekData, MarstekProtocol


def test_device_info_ignores_malformed_tokens_and_tracks_only_present_fields() -> None:
    data = MarstekData()

    assert MarstekProtocol._parse_device_info(
        b"malformed,type = HMG-50,also-malformed,unknown=value",
        data,
        10.0,
    )

    assert data.device_type == "HMG-50"
    assert data.device_id is None
    assert data.serial_number is None
    assert data.mac_address is None
    assert data.firmware_version is None
    assert data.hardware_version is None
    assert set(data.field_updates) == {"device_type"}


def test_network_info_ignores_malformed_and_unknown_pairs() -> None:
    data = MarstekData()

    assert MarstekProtocol._parse_network_info(
        b"malformed,unknown:value, ip : 192.0.2.10 , gateway : 192.0.2.1 ",
        data,
        20.0,
    )

    assert data.ip_address == "192.0.2.10"
    assert data.gateway == "192.0.2.1"
    assert data.subnet_mask is None
    assert data.dns_server is None
    assert set(data.field_updates) == {
        "network_info",
        "ip_address",
        "gateway",
    }
