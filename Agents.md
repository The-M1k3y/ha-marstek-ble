# Agent instructions

## Use the OKF bundle first

Repository knowledge intended for agents is stored in `docs/OKF/` using Open
Knowledge Format v0.2.

1. Start with `docs/OKF/index.md`.
2. Read `docs/OKF/scope.md` before using protocol knowledge.
3. Open only the linked concepts relevant to the current task.
4. Follow concept links and inspect each document's `sources`, `status`,
   `generated`, and `source_revision` frontmatter.

The OKF bundle is a curated navigation and context layer. Source code remains
authoritative. When a concept conflicts with the current branch, inspect the
code and update the knowledge rather than coding from stale prose.

## Product scope and contamination guard

Venus and Jupiter protocol knowledge must remain product-specific unless a
committed source explicitly supports a shared abstraction.

- Do not infer that a command number, payload offset, scale, status bit, cell
  count, entity, or control has the same meaning across products.
- Add product knowledge only from explicit repository sources introduced for
  that product.
- Keep tentative or implementation-derived interpretations qualified; do not
  present them as vendor-confirmed facts.
- The sanitized Jupiter source is
  `docs/sources/jupiter-c-plus-ble-field-map.md`. It contains structural field
  mappings only.

## Private diagnostics and sensitive information

Never commit complete diagnostic captures, BLE frames, payload hex, timestamps
from private captures, device or cloud identifiers, MAC addresses, Wi-Fi names,
observed telemetry values, capture-specific counters, or captured event records.

Do not reconstruct such material from conversation history, private diagnostics,
uncommitted reports, or earlier experiments. When a proposed repository change
might expose personal, identifying, network, or otherwise sensitive information,
ask the repository owner before writing it.

Sanitized protocol structure may include command numbers, payload lengths,
offsets, field types, canonical units, confidence labels, and semantic names when
those details are explicitly approved as repository knowledge.

## Source precedence

Use this precedence when resolving discrepancies:

1. executable source and tests on the branch being modified;
2. sanitized, committed protocol sources under `docs/sources/`;
3. immutable resources listed in a concept's `sources`;
4. current repository documentation; and
5. external references explicitly cited by repository documentation.

Conversation history, private diagnostics, uncommitted reports, and prior
experiments are not repository sources unless the user explicitly asks to use
them, they are within product scope, and sensitive material is excluded.

## Updating OKF knowledge

When a code change alters documented behavior:

1. update every affected concept under `docs/OKF/`;
2. set `source_revision` to the commit containing the new behavior once known;
3. update `generated.at` for a meaningful content change;
4. preserve or refresh `sources` with stable, preferably revision-pinned
   resources;
5. add a newest-first entry to `docs/OKF/log.md` using an ISO `YYYY-MM-DD`
   heading;
6. update `docs/OKF/index.md` when concepts are added, moved, renamed, or
   deprecated; and
7. keep `status: draft` unless a human has actually reviewed the concept.

Do not invent `verified` events. A human review must be represented by a real
`human:<id>` actor and timestamp.

## OKF formatting rules

- Every concept document must begin with YAML frontmatter and include `type`.
- `index.md` and `log.md` are reserved filenames; do not use them for ordinary
  concepts.
- The bundle-root `index.md` carries `okf_version: "0.2"` and provides
  progressive disclosure.
- Prefer structured Markdown: headings, tables, lists, and fenced examples.
- Keep Markdown table columns padded and delimiter rows aligned so tables remain
  readable in a monospace editor; realign the complete table after changing any
  cell.
- Order protocol field tables by byte offset, including unknown and unused
  ranges in their actual positions rather than grouping fields logically.
- Use normal Markdown links between concepts; keep links relative to
  `docs/OKF/` where practical.
- Each `sources` entry must include `resource`.
- Preserve unknown frontmatter fields when editing a concept.
- Broken links are tolerated by OKF but should not be introduced intentionally.

## Multi-product changes

Before integrating another product, identify and isolate the current product
coupling points documented in `docs/OKF/architecture.md`: discovery patterns,
model metadata, protocol/parser selection, poll schedules, capabilities, field
schemas, entity definitions, and cell or expansion limits.

Prefer explicit product profiles and strategies over command-number conditionals
spread across entity platforms. Entity and control creation must be
capability-aware so unsupported fields do not appear as valid stale data.

The declarative model under `custom_components/marstek_ble/schema.py`,
`entity.py`, and `products/` is connected to the live sensor and binary-sensor
platforms. Extend read-only product entities through product-profile metadata and
the shared entity-plan infrastructure rather than adding product-specific entity
lists to platform modules. Venus currently remains the only product with enabled
write/control platforms; do not expose those controls for another product unless
its command semantics are explicitly validated.

## Unit-test discipline

- Run the complete isolated unit-test suite before every commit. Use
  `pytest -m "not known_issue"` for the passing baseline and
  `pytest -m "not known_issue" --cov --cov-report=term-missing` for coverage.
  Do not introduce unaccounted failures.
- Coverage has no file-level exceptions. Every Python source file under the
  configured coverage roots (`custom_components/marstek_ble` and
  `standalone_test`) must remain included in coverage collection; do not add
  `omit` rules or equivalent source exclusions to hide untested code.
- Treat missing statement and branch coverage as test-design information, not as
  a reason to exclude code. Prefer tests that exercise meaningful normal,
  boundary, failure, lifecycle, and topology paths over assertions written only
  to increase a percentage.
- Every newly added function must be accompanied by a dedicated set of tests
  covering its normal behavior, boundary conditions, and relevant failure
  paths.
- Never change production code and tests in the same commit. Use distinct
  test-only and code-only commits, and do not weaken or rewrite tests merely to
  make a production change pass.
- Unit tests must run in an isolated environment without a real Home Assistant
  installation or instance, network access, Bluetooth hardware, an ESPHome
  proxy, or a physical Marstek device. Replace external systems with deterministic
  stubs, fakes, or mocks.
- Keep defect tests as ordinary failures marked `known_issue`; do not skip,
  remove, or convert them to expected failures without explicit approval from
  the repository owner.
