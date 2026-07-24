---
name: nostdb
description: Initialize, remove, explain, model, populate, inspect, query, validate, and maintain NostDB source projects. Use for `nostdb init`, `nostdb remove`, `nostdb help`, source setup or cleanup, Schema or Constraint design, document or code ingestion, graph exploration, canonical formatting, synchronization, diagnostics, or any end-to-end NostDB workflow other than graph visualization.
---

# Work with NostDB

Route an explicit leading action before the general workflow:

- `help`: Respond directly from this file without running Python, inspecting a
  project, resolving the CLI, or modifying files. State that `nostdb` supports
  guarded NDB-only initialization, scoped removal, source configuration,
  Schema/Constraint design, ingestion, querying, diagnostics, and maintenance;
  direct graph visualization belongs to `nostdb-visualize`. Mention that
  initialization defaults to Core `0.0.2` with provider `auto`.
- `init`: Read [safety.md](references/safety.md), [project.md](references/project.md), and [core-providers.md](references/core-providers.md). Require the intended project root, inspect whether it is empty, then initialize the configured `.nostdb` without exposing source:

```bash
python3 <skill-root>/scripts/nostdb_skill.py init \
  --src <src> --core-provider auto
```

Add `--allow-nonempty` only after confirming an existing nonempty directory is
the intended project. Preserve the default exact Core version unless the user
requests a supported migration. The wrapper resolves the provider, delegates
project configuration and database creation to native `nostdb init` when the
resolved CLI supports it, then records Agent-specific provider metadata. The
published Core `0.0.2` predates native `init`, so the wrapper uses its guarded
in-process configuration plus native `sync` compatibility path for that
provider. Report the configuration and root `.nostdb`; `.nost` must remain
absent while `nost` is false.
- `remove`: Read [safety.md](references/safety.md) and [project.md](references/project.md). Require explicit confirmation of the exact project root, inspect its Git changes, and stop any database owner. Run the bundled helper rather than deleting paths ad hoc:

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

1. Require the intended project root. Inspect `nostdb.json`, the configured
   `.nostdb`, optional `.nost` modules, and Git changes; preserve unrelated work.
2. Initialize NDB-only by default. Enable `nost` and synchronize before
   creating or directly editing `.nost`.
3. Resolve the exact configured CLI before semantic work:

```bash
python3 <skill-root>/scripts/nostdb_core.py resolve \
  --src <src> --json
```

4. Use the selected task reference. Database queries write `.nostdb` first. For
   direct source work, preserve Stable Module IDs, operate on complete `.nost`
   files through the guarded workflow, and treat Core diagnostics as
   authoritative.
5. After a source change, invoke the CLI only through the same wrapper to format, synchronize, and diagnose:

```bash
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  format --file <owner.nost> --project <src> --check
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  sync --project <src> --format json
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  doctor --project <src> --format json
```

6. Report changed source and configuration files, commands, warnings, unresolved references, constraint failures, and source conflicts.

`--src` is the Skill-wrapper source-root option. Arguments after `--` belong to
the native CLI, whose local-project option is `--project`.

Use `nostdb-visualize` when the requested outcome is a diagram or visualization dataset. Never open, generate, patch, or interpret `.nostdb` bytes; only the resolved CLI may create or update the database.
