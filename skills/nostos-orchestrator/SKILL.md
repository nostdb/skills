---
name: nostos-orchestrator
description: Coordinate a complete NostosDB Source Mode workflow across project setup, schema design, ingestion, exploration, and visualization. Use when starting a graph project, choosing a source layout, routing work among Nostos skills, or validating an end-to-end .nostos-to-.ndb workflow.
---

# Orchestrate NostosDB work

1. Read [project.md](../../references/project.md) and [safety.md](../../references/safety.md).
2. Require an explicit intended project directory. Inspect its contents, `nostos.toml`, existing `.nostos` modules, Git changes, and the requested outcome. Preserve unrelated edits; do not initialize inside a nonempty unrelated directory by inference.
3. If the project is new, choose `centralized`, `colocated`, or `single` from the project evidence and persist it with `nostos_project.py init`. Do not silently change an existing layout.
4. Immediately after initialization, resolve the exact pinned CLI with `nostos_core.py resolve`. Make no semantic source edit unless resolution succeeds.
5. Route specialized work:
   - use `nostos-schema` for Schemas and Constraints;
   - use `nostos-ingest` for document or code-derived entities and provenance;
   - use `nostos-explore` for bounded graph questions;
   - use `nostos-visualize` for graph views;
   - use `nostos-core` for deterministic format, sync, check, doctor, and query commands.
6. Format every changed source through `nostos format --file <file> --project <project>`, replace the complete file with that stdout through the guarded source workflow, then run `format --check`, `sync`, `check`, and `doctor`.
7. Report changed `.nostos` and configuration files, Core commands, warnings, unresolved references, and any source conflict.

Never generate, patch, or interpret `.ndb` bytes. Only the resolved public CLI may create or update `.ndb`.
