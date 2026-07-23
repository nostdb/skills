# Schema and Constraint workflow

1. Inspect current declarations, representative data, unresolved Schemas, and validation mode before proposing a change.
2. Prefer the smallest reusable Schema set. Treat Node and Edge use as application of generic Schemas; do not duplicate types per module without evidence.
3. Separate soft type and unknown-property validation from hard explicit Constraints. Before adding `required`, `unique`, or endpoint Constraints, query all affected data and report violations.
4. Preserve Stable Module IDs and source ownership. Never edit an imported read-only module automatically.
5. Rewrite the complete owner file, retain comments, canonicalize it through the pinned CLI, and show the diff.
6. Run `sync` and `doctor`. Treat a hard-Constraint failure as a rejected migration rather than a warning to bypass.

Do not add unsupported syntax or implement validation in the Skill. Deterministic Core diagnostics are authoritative.
