# Agent instructions

## Use the OKF bundle first

Repository knowledge intended for agents is stored in `docs/OKF/` using Open Knowledge Format v0.2.

1. Start with `docs/OKF/index.md`.
2. Read `docs/OKF/scope.md` before using protocol knowledge.
3. Open only the linked concepts relevant to the current task.
4. Follow concept links and inspect each document's `sources`, `status`, `generated`, and `source_revision` frontmatter.

The OKF bundle is a curated navigation and context layer. Source code remains authoritative. When a concept conflicts with the current branch, inspect the code and update the knowledge rather than coding from stale prose.

## Product scope and contamination guard

The existing protocol concepts describe Venus units as implemented by this repository.

- Do not add Jupiter-C reverse-engineering information, packet captures, offsets, hypotheses, or remembered findings to this repository or its OKF bundle.
- Do not infer that a Venus command, payload offset, scale, status bit, cell count, or entity applies to another product.
- Add knowledge for a new product only from explicit repository sources introduced for that product.
- Keep product-specific protocol concepts separate until committed evidence supports a shared abstraction.
- Mark tentative or implementation-derived interpretations as such; do not present them as vendor-confirmed facts.

## Source precedence

Use this precedence when resolving discrepancies:

1. executable source and tests on the branch being modified;
2. immutable resources listed in a concept's `sources`;
3. current repository documentation;
4. external references explicitly cited by repository documentation.

Conversation history, private diagnostics, uncommitted reports, and prior experiments are not valid sources for the OKF bundle unless the user explicitly asks to add them and they are within the product scope.

## Updating OKF knowledge

When a code change alters documented behavior:

1. update every affected concept under `docs/OKF/`;
2. set `source_revision` to the commit containing the new behavior once known;
3. update `generated.at` for a meaningful content change;
4. preserve or refresh `sources` with stable, preferably revision-pinned resources;
5. add a newest-first entry to `docs/OKF/log.md` using an ISO `YYYY-MM-DD` heading;
6. update `docs/OKF/index.md` when concepts are added, moved, renamed, or deprecated; and
7. keep `status: draft` unless a human has actually reviewed the concept.

Do not invent `verified` events. A human review must be represented by a real `human:<id>` actor and timestamp.

## OKF formatting rules

- Every concept document must begin with YAML frontmatter and include `type`.
- `index.md` and `log.md` are reserved filenames; do not use them for ordinary concepts.
- The bundle-root `index.md` carries `okf_version: "0.2"` and provides progressive disclosure.
- Prefer structured Markdown: headings, tables, lists, and fenced examples.
- Keep Markdown table columns padded and delimiter rows aligned so tables remain readable in a monospace editor; realign the complete table after changing any cell.
- Order protocol field tables by byte offset, including unknown and unused ranges in their actual positions rather than grouping fields logically.
- Use normal Markdown links between concepts; keep links relative to `docs/OKF/` where practical.
- Each `sources` entry must include `resource`.
- Preserve unknown frontmatter fields when editing a concept.
- Broken links are tolerated by OKF but should not be introduced intentionally.

## Multi-product changes

Before adding another product, identify and isolate the current Venus coupling points documented in `docs/OKF/architecture.md`: discovery patterns, model metadata, protocol/parser selection, poll schedules, capabilities, field schemas, and cell count. Prefer explicit product profiles or strategies over command-number conditionals spread across entity platforms.

A universal result object may retain fields not supplied by a product-specific schema, but entities and controls must be capability-aware so unsupported fields do not appear as valid stale data.
