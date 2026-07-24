# Canonical reference sources

The general `nostdb` Skill and the separate `nostdb-visualize` Skill load only the reference needed for a task:

- `safety.md`: authority, source-editing, and `.nostdb` boundaries
- `project.md`: `.nostdb/` layout, `settings.json`, nested links, and Core pinning
- `core-providers.md`: installed-first and pinned-npx fallback contract
- `schema.md`: Schema and hard-Constraint evolution workflow
- `ingest.md`: document/code extraction and guarded source installation
- `provenance.md`: deterministic document/code evidence records
- `query.md`: bounded query and administration rules

The standalone Skill directories contain the runtime copies they need. Repository verification requires those copies to match the canonical development sources, with `visualize-query.md`, `nostdb_visualize_core.py`, and the visualization-only safety policy tailored to the read-only Skill.
