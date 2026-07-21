# Canonical reference sources

The general `nostos` Skill and the separate `nostos-visualize` Skill load only the reference needed for a task:

- `safety.md`: authority, source-editing, and `.ndb` boundaries
- `project.md`: layouts, `nostos.toml`, and Core pinning
- `core-providers.md`: installed-first and pinned-npx fallback contract
- `schema.md`: Schema and hard-Constraint evolution workflow
- `ingest.md`: document/code extraction and guarded source installation
- `provenance.md`: deterministic document/code evidence records
- `query.md`: bounded query and administration rules

The standalone Skill directories contain the runtime copies they need. Repository verification requires those copies to match these canonical development sources, except for the visualization-only safety policy tailored to its read-only scope.
