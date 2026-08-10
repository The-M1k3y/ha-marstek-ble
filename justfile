set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

python := env_var_or_default("PYTHON", "python3")
ha_python := env_var_or_default("HA_PYTHON", "python3.14")
ha_deploy_config := ".ha-deploy.conf"

# List the available project recipes.
default:
    @just --list

# Install dependencies for the isolated test suite.
install:
    {{python}} -m pip install -r requirements-test.txt

# Install isolated-test, tox, and mutation-testing dependencies.
install-quality: install
    {{python}} -m pip install -r requirements-test-quality.txt

# Install dependencies for the genuine Home Assistant test harness.
install-ha:
    {{ha_python}} -m pip install -r requirements-test-ha.txt

# Install every development and test dependency supported by the repository.
install-all: install-quality install-ha

# Compile Python sources and tests to detect syntax errors.
compile:
    {{python}} -m compileall -q custom_components standalone_test tests tests_ha

# Run the passing isolated baseline, excluding documented production defects.
test:
    {{python}} -m pytest -m "not known_issue"

# Run only the documented production-defect tests.
test-known-issues:
    {{python}} -m pytest -m "known_issue"

# Run the complete isolated suite with coverage, including known defects.
test-full:
    {{python}} -m pytest --cov --cov-report=term-missing

# Run the passing isolated baseline with terminal coverage details.
coverage:
    {{python}} -m pytest -m "not known_issue" --cov --cov-report=term-missing

# Generate an HTML coverage report for the passing isolated baseline.
coverage-html:
    {{python}} -m pytest -m "not known_issue" --cov --cov-report=term-missing --cov-report=html

# Run one pytest path or node ID.
test-file path:
    {{python}} -m pytest "{{path}}"

# Run passing isolated tests selected by a pytest -k expression.
test-match expression:
    {{python}} -m pytest -m "not known_issue" -k "{{expression}}"

# Run tests against the genuine Home Assistant framework.
test-ha:
    {{ha_python}} -m pytest -c pytest-ha.ini

# Run the isolated passing baseline across available supported Python versions.
test-matrix:
    {{python}} -m tox

# Run the genuine Home Assistant test environment through tox.
test-matrix-ha:
    {{python}} -m tox -e ha

# Run syntax checks and the passing isolated baseline.
check: compile test

# Run both mandatory pre-commit suites; known_issue tests may make this fail.
verify: compile test test-full

# Measure the passing baseline and then run mutation testing.
mutation: coverage
    mutmut run

# Show mutation-testing result totals.
mutation-results:
    mutmut results

# Browse surviving mutations interactively.
mutation-browse:
    mutmut browse

# Upload the integration source to the configured Home Assistant instance.
ha-upload:
    @test -f "{{ha_deploy_config}}" || { echo "Missing {{ha_deploy_config}}; copy {{ha_deploy_config}}.example and edit it." >&2; exit 1; }
    @source "{{ha_deploy_config}}"; : "${HA_SSH_TARGET:?HA_SSH_TARGET is required}" "${HA_SSH_PORT:?HA_SSH_PORT is required}" "${HA_CONFIG_DIR:?HA_CONFIG_DIR is required}"; tar -C custom_components -cf - marstek_ble | ssh -p "$HA_SSH_PORT" "$HA_SSH_TARGET" "set -eu; rm -rf '$HA_CONFIG_DIR/custom_components/marstek_ble'; mkdir -p '$HA_CONFIG_DIR/custom_components'; tar -xf - -C '$HA_CONFIG_DIR/custom_components'"

# Restart Home Assistant Core using the configured remote command.
ha-restart:
    @test -f "{{ha_deploy_config}}" || { echo "Missing {{ha_deploy_config}}; copy {{ha_deploy_config}}.example and edit it." >&2; exit 1; }
    @source "{{ha_deploy_config}}"; : "${HA_SSH_TARGET:?HA_SSH_TARGET is required}" "${HA_SSH_PORT:?HA_SSH_PORT is required}" "${HA_RESTART_COMMAND:?HA_RESTART_COMMAND is required}"; ssh -p "$HA_SSH_PORT" "$HA_SSH_TARGET" "$HA_RESTART_COMMAND"

# Upload the integration and restart Home Assistant Core.
ha-deploy: ha-upload ha-restart

# Remove local Python, pytest, coverage, tox, and mutation-test artifacts.
clean:
    rm -rf .coverage .coverage.* .pytest_cache .tox htmlcov mutants .mutmut-cache
    find custom_components standalone_test tests tests_ha -type d -name __pycache__ -prune -exec rm -rf {} +
    find custom_components standalone_test tests tests_ha -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
