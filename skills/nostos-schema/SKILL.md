---
name: nostos-schema
description: Design and maintain NostosDB Schemas and explicit Constraints in canonical .nostos source. Use when modeling node or edge properties, selecting validation modes, introducing required or unique fields, defining endpoint constraints, or reviewing a schema migration.
---

# Design and evolve Schemas

1. Read [safety.md](../../references/safety.md) and [project.md](../../references/project.md).
2. Inspect current declarations, data examples, unresolved Schemas, and validation mode before proposing changes.
3. Prefer the smallest reusable Schema set. Treat Node/Edge use as application of generic Schemas; do not duplicate types per module without evidence.
4. Separate soft type/unknown-property validation from hard explicit Constraints. Before adding `required`, `unique`, or endpoint Constraints, query all affected data and describe violations.
5. Preserve Stable Module IDs and source ownership. Never edit an imported read-only module automatically.
6. Rewrite the complete owner file, retain comments, canonicalize through `nostos format`, and show the diff.
7. Run `sync` and `doctor`. A hard-Constraint failure is a rejected migration, not a warning to bypass.

Do not add unsupported syntax or implement validation in the Skill. Deterministic Core diagnostics are authoritative.
