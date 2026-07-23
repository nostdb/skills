---
name: nostdb
description: Initialize, remove, explain, model, populate, inspect, query, validate, and maintain centralized NostDB source projects. Use for `nostdb init`, `nostdb remove`, `nostdb help`, source setup or cleanup, Schema or Constraint design, document or code ingestion, graph exploration, canonical formatting, synchronization, diagnostics, or any end-to-end NostDB workflow other than graph visualization.
---

# Work with NostDB

Route an explicit leading action before the general workflow:

- `help`: Run `python3 <skill-root>/scripts/nostdb_skill.py help` and return its stdout. Do not require or inspect a project, resolve the CLI, or modify files.
- `init`: Read [safety.md](references/safety.md), [project.md](references/project.md), and [core-providers.md](references/core-providers.md). Require the intended source root, inspect whether it is empty, then initialize the fixed `centralized` layout:

```bash
python3 <skill-root>/scripts/nostdb_skill.py init \
  --src <src> --core-provider auto
```

Add `--allow-nonempty` only after confirming an existing nonempty directory is the intended project. Preserve the default exact Core version unless the user requests a supported migration. Report the created configuration and source path, then stop; initialization alone does not require CLI resolution or synchronization.
- `remove`: Read [safety.md](references/safety.md) and [project.md](references/project.md). Require explicit confirmation of the exact source root, inspect its Git changes, and stop any database owner. Run the bundled helper rather than deleting paths ad hoc:

```bash
python3 <skill-root>/scripts/nostdb_skill.py remove --src <src>
```

Use `--dry-run` first when the requested scope is not already explicit. Report
every removed path. The helper deletes only recognized project-local NostDB
configuration, sources, databases, sidecars, locks, and temporary files; it
preserves unrelated files and refuses broad roots, symlink boundaries, or an
open database. Stop after removal.

For any other action, read [safety.md](references/safety.md), [project.md](references/project.md), and [core-providers.md](references/core-providers.md). Read only the additional task reference needed:

- Schema or Constraint work: [schema.md](references/schema.md)
- Document or code ingestion: [ingest.md](references/ingest.md) and [provenance.md](references/provenance.md)
- Graph inspection or exploration: [query.md](references/query.md)

1. Require the intended source root. Inspect its files, `nostdb.json`, `.nost` modules, imports, and Git changes; preserve unrelated work.
2. Initialize new source only with the fixed `centralized` layout. Never silently change an existing layout or initialize an unrelated nonempty directory.
3. Resolve the exact configured CLI before semantic work:

```bash
python3 <skill-root>/scripts/nostdb_core.py resolve \
  --src <src> --json
```

4. Use the selected task reference. Preserve Stable Module IDs and source ownership, operate on complete `.nost` files through the guarded source workflow, and treat Core diagnostics as authoritative.
5. After a source change, invoke the CLI only through the same wrapper to format, synchronize, and diagnose:

```bash
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  format --file <owner.nost> --project <src> --check
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  sync --project <src> --database <src>/<skills.database> --format json
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  check --database <src>/<skills.database> --format json
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  doctor --project <src> --database <src>/<skills.database> --format json
```

6. Report changed source and configuration files, commands, warnings, unresolved references, constraint failures, and source conflicts.

`--src` is the Skill-wrapper source-root option. Arguments after `--` belong to
the native CLI, whose Source Mode option remains `--project`.

Use `nostdb-visualize` when the requested outcome is a diagram or visualization dataset. Never open, generate, patch, or interpret `.nostdb` bytes; only the resolved CLI may create or update the database.
