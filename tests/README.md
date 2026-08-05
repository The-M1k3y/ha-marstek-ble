# Unit tests

These tests cover the original Venus-oriented integration under
`custom_components/marstek_ble/` and the original ESPHome proxy utility under
`standalone_test/`. The branch-only declarative model in
`schema.py`, `entity.py`, and `products/` is intentionally excluded until it is
integrated into the production code.

The test environment supplies lightweight stubs for Home Assistant, BLE, and
ESPHome API libraries. No Home Assistant installation, Bluetooth adapter,
ESPHome proxy, network access, or Marstek device is required.

Install and run:

```bash
python -m pip install -r requirements-test.txt
pytest -m "not known_issue"
pytest --cov --cov-report=term-missing
```

Tests marked `known_issue` are ordinary failing tests, not skips or expected
failures. The full run therefore acts as an issue inventory. The filtered run
must pass and confirms that no unrelated regression was introduced.
