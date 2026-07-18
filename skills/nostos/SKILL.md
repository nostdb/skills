---
name: nostos
description: Create, model, populate, inspect, query, validate, and maintain NostosDB projects. Use for project setup, source layout, Schema or Constraint design, document or code ingestion, graph exploration, canonical formatting, synchronization, diagnostics, or any end-to-end NostosDB workflow other than graph visualization.
---

# Work with NostosDB

Read [safety.md](../../references/safety.md), [project.md](../../references/project.md), and [core-providers.md](../../references/core-providers.md). Read only the additional task reference needed:

- Schema or Constraint work: [schema.md](../../references/schema.md)
- Document or code ingestion: [ingest.md](../../references/ingest.md) and [provenance.md](../../references/provenance.md)
- Graph inspection or exploration: [query.md](../../references/query.md)

1. Require the intended project directory. Inspect its files, `nostos.toml`, `.nostos` modules, imports, and Git changes; preserve unrelated work.
2. Initialize a new project only after selecting `centralized`, `colocated`, or `single` from project evidence. Never silently change an existing layout or initialize an unrelated nonempty directory.
3. Resolve the exact configured CLI before semantic work:

```bash
python3 <skill-root>/../../scripts/nostos_core.py resolve \
  --project <project> --json
```

4. Use the selected task reference. Preserve Stable Module IDs and source ownership, operate on complete `.nostos` files through the guarded source workflow, and treat Core diagnostics as authoritative.
5. After a source change, invoke the CLI only through the same wrapper to format, synchronize, and diagnose:

```bash
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  format --file <owner.nostos> --project <project> --check
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  sync --project <project> --database <project>/<skills.database> --format json
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  check --database <project>/<skills.database> --format json
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  doctor --project <project> --database <project>/<skills.database> --format json
```

6. Report changed source and configuration files, commands, warnings, unresolved references, constraint failures, and source conflicts.

Use `nostos-visualize` when the requested outcome is a diagram or visualization dataset. Never open, generate, patch, or interpret `.ndb` bytes; only the resolved CLI may create or update the database.
