"""Fixtures for tests using the genuine Home Assistant test harness."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest
import pytest_socket


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Allow the harness to load the integration from custom_components."""
    yield


@pytest.fixture(autouse=True)
def _allow_home_assistant_unix_sockets():
    """Allow Home Assistant local IPC while blocking non-loopback network access."""
    pytest_socket.socket_allow_hosts(
        ["127.0.0.1"],
        allow_unix_socket=True,
    )
