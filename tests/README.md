# Isolated tests

These tests cover the original Venus-oriented integration under
`custom_components/marstek_ble/` and the original ESPHome proxy utility under
`standalone_test/`. The branch-only declarative model in `schema.py`,
`entity.py`, and `products/` remains excluded until it is integrated into the
production code.

The default test environment supplies lightweight stubs for Home Assistant,
BLE, and ESPHome API libraries. It requires no Home Assistant installation or
instance, Bluetooth adapter, ESPHome proxy, network access, or Marstek device.
All packet replay data is generated and contains no captured identifiers or
telemetry.

## Default suite

Install and run:

```bash
python -m pip install -r requirements-test.txt
pytest -m "not known_issue"
pytest --cov --cov-report=term-missing
```

The default suite includes:

- example-based unit tests;
- deterministic property and malformed-input fuzz tests;
- asynchronous connection, command, cancellation, and response-order tests;
- synthetic packet replay fixtures; and
- manifest, HACS, platform, translation-string, import-boundary, and packaging
  contracts.

Tests marked `known_issue` are ordinary failing tests, not skips or expected
failures. The full run therefore acts as an issue inventory. The filtered run
must pass and confirms that no unrelated regression was introduced.

## Genuine Home Assistant harness

The separate `tests_ha/` suite runs against the real Home Assistant testing
framework while still mocking Bluetooth and using an in-memory Home Assistant
instance. It is kept outside `tests/` so the lightweight default suite never
imports the real framework.

Use Python 3.14 and run:

```bash
python -m pip install -r requirements-test-ha.txt
pytest -c pytest-ha.ini
```

This suite checks the real flow manager, option flow, config-entry lifecycle,
and custom-integration loading behavior.

## Python compatibility

Run the passing isolated baseline on the configured Python matrix:

```bash
python -m pip install -r requirements-test-quality.txt
tox
```

Run the genuine Home Assistant suite through tox when Python 3.14 is installed:

```bash
tox -e ha
```

Tox skips unavailable interpreters rather than downloading or provisioning
one.

## Mutation testing

Mutation testing is intentionally separate because it is substantially slower
than normal tests. The configuration mutates only original integration and
standalone code, excludes the branch-only declarative model, and uses the
passing baseline rather than the known-defect inventory.

```bash
python -m pip install -r requirements-test.txt -r requirements-test-quality.txt
pytest -m "not known_issue" --cov
mutmut run
mutmut browse
```

Run mutmut on a platform with process-fork support. Its results are a test
quality report, not a release gate with a predefined required mutation score.
