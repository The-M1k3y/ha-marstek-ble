---
type: Software Testing
title: Isolated testing and coverage
description: Repository test layers, known-issue handling, complete coverage scope, and coverage-driven test design.
tags: [testing, pytest, coverage, isolation, known-issue]
status: draft
source_revision: "f68af61acc7833fab5117e327e2446a1b88e3dd2"
generated: { by: openai/gpt-5.6-sol, at: 2026-08-08T16:57:00Z }
sources:
  - id: coverage-config
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/a7d9037ff6c87f84c7f0b6df9f9130c5f12a6869/.coveragerc
    title: Coverage collection configuration
  - id: declarative-coverage-tests
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/8c20923c23dcb6541325bf78dad41bb8338e39c7/tests/test_declarative_coverage.py
    title: Declarative schema, entity-plan, and Jupiter tests
  - id: pytest-config
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/df5892d6de68fac6316de7e21a5327bbf3f8fa95/pytest.ini
    title: Pytest configuration and known-issue marker
  - id: agent-policy
    resource: https://github.com/The-M1k3y/ha-marstek-ble/blob/f68af61acc7833fab5117e327e2446a1b88e3dd2/Agents.md
    title: Repository test and coverage discipline
---

# Purpose

The repository test suite is designed to exercise the integration, protocol, and standalone tooling in an isolated environment. Tests must not require a live Home Assistant instance, network access, Bluetooth hardware, an ESPHome proxy, or a physical Marstek device.

# Passing baseline

The normal passing baseline excludes tests explicitly marked `known_issue`:

```text
pytest -m "not known_issue"
```

Coverage uses the same passing selection so known production defects do not prevent collection:

```text
pytest -m "not known_issue" --cov --cov-report=term-missing
```

`known_issue` is a defect marker, not a coverage exclusion. Tests carrying the marker remain ordinary regression expectations and must not be skipped, deleted, weakened, or converted to expected failures without explicit owner approval.

# Coverage scope

Coverage collection has no file-level exceptions. `.coveragerc` includes both repository source roots:

- `custom_components/marstek_ble`
- `standalone_test`

There is no `omit` list. Every Python source file under those roots therefore participates in coverage reporting, including declarative or not-yet-runtime-enabled product definitions such as `products/jupiter.py`.

A low percentage is expected to expose missing tests rather than justify a source exclusion. Coverage configuration must not be used to hide untested code.

# Coverage-driven test design

Coverage is used to identify unexercised behavior, with branch and failure paths considered alongside statement coverage. Tests should target meaningful behavior rather than percentage-only execution.

The declarative coverage tests directly exercise areas that were previously omitted or lightly covered:

- packet-schema construction and payload bounds;
- field-source validation, explicit endianness, length gates, tuple parsing, and conversion failures;
- nested and repeated-section parsing, including atomic parse failure;
- schema helper converters and invalid arguments;
- field/entity metadata builders and accessors;
- entity-plan value lookup, unique keys, repeated counts, presence predicates, and error paths;
- expansion-increase detection and child-device identifiers;
- Jupiter runtime-summary parsing;
- Jupiter detailed telemetry and repeated battery-pack parsing;
- Jupiter event-history parsing across all fixed records;
- Jupiter child-device planning and expansion topology; and
- Jupiter derived battery-power and charging entities.

# Test/change separation

Production code and its tests must not be changed in the same commit. Test-only and code-only changes remain separate so a regression expectation is independently reviewable and cannot be silently adjusted together with the implementation it verifies.

Documentation and test configuration changes do not alter production behavior, but they should still preserve the same isolated-test guarantees.

# Interpreting a coverage report

Prioritize uncovered paths in this order:

1. correctness-critical parsing, validation, state mutation, and lifecycle branches;
2. negative and exception-handling paths;
3. topology, presence, stale-data, and boundary behavior;
4. Home Assistant setup/unload and platform behavior; and
5. defensive branches that are difficult to reach but still represent plausible states.

A reported line should not automatically receive a test when execution would only assert an implementation detail with no useful behavioral contract. Conversely, an apparently high-covered module can still need tests when branch coverage or failure behavior is weak.
