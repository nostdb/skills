---
name: nostdb
description: Initialize, update, remove, explain, model, populate, inspect, query, validate, and maintain NostDB source projects. Use for `nostdb init`, `nostdb update`, `nostdb remove`, `nostdb help`, project discovery, nested project linking, source setup or cleanup, Schema or Constraint design, document or code ingestion, graph exploration, canonical formatting, synchronization, diagnostics, or any end-to-end NostDB workflow other than graph visualization.
---

# Work with NostDB

Route an explicit leading action before the general workflow:

- `help`: Respond directly from this file without running Python, inspecting a
  project, resolving the CLI, or modifying files. Always use this exact compact
  shape, in this order, with no preamble or feature essay:

  ```text
  nostdb actions

  init     Create a guarded NDB-only project
  update   Synchronize databases and optionally create matching .nost files
  remove   Delete one explicitly confirmed project scope
  model    Design Schemas, Constraints, and graph structure
  ingest   Load documents or code with provenance
  query    Inspect or query the configured database
  maintain Diagnose, format, synchronize, or repair source state

  Choose one action and provide the project root when required.
  ```

  Keep each action description verb-first and route visualization requests to
  `nostdb-visualize`. Initialization defaults to Core `0.0.3` with provider
  `auto`. Do not invent a `help` subcommand or run a helper script for this
  response.
- `init`: Read [safety.md](references/safety.md),
  [project.md](references/project.md), and
  [core-providers.md](references/core-providers.md). Require the intended
  project root and inspect whether it is empty. Run:

```bash
python3 <skill-root>/scripts/nostdb_skill.py init \
  --src <src> --core-provider auto
```

Add `--allow-nonempty` only after confirming an existing nonempty directory is
the intended project. Preserve the exact Core version unless the user requests
a supported migration. The native CLI creates `.nostdb/settings.json` and
`.nostdb/root.nostdb`; the wrapper records Agent-specific provider metadata.
No `.nost` file exists while `source.enabled` is false.
- `update`: Read [safety.md](references/safety.md),
  [project.md](references/project.md), and the task-specific modeling or
  ingestion reference. Inspect project manifests, source directories, and
  existing `.nostdb/` child projects. Update complete canonical `.nost` modules
  below the selected project's `.nostdb/` to reflect the current project, then
  run:

```bash
python3 <skill-root>/scripts/nostdb_skill.py update --src <src> [--nost]
```

Pass `--nost` when the user asks to create human-readable source. It enables
source materialization and delegates to Core; for a configured database such
as `.nostdb/root.nostdb`, the canonical single-module file is
`.nostdb/root.nost` (the `.nost` basename always matches the `*.nostdb`
basename). Without `--nost`, source visibility is unchanged.

The helper discovers nearest nested projects without crossing symlinks or
generated dependency directories, refreshes `database.links`, and invokes
native `nostdb update` so child root databases synchronize before the parent.
Report inspected inputs, changed `.nost` files, linked projects, diagnostics,
and database generations.
- `remove`: Read [safety.md](references/safety.md) and
  [project.md](references/project.md). Require explicit confirmation of the
  exact project root, inspect its Git changes, and stop every database owner.
  Run the bundled helper rather than deleting paths ad hoc:

```bash
python3 <skill-root>/scripts/nostdb_skill.py remove --src <src>
```

Use `--dry-run` first when the scope is not explicit. The helper deletes only
recognized project-local `.nostdb/` directories, preserves unrelated files, and
refuses broad roots, symlink boundaries, or open databases. Stop after removal.

For any other action, read [safety.md](references/safety.md),
[project.md](references/project.md), and
[core-providers.md](references/core-providers.md). Read only the additional
task reference needed:

- Schema or Constraint work: [schema.md](references/schema.md)
- Document or code ingestion: [ingest.md](references/ingest.md) and
  [provenance.md](references/provenance.md)
- Graph inspection or exploration: [query.md](references/query.md)

1. Require the intended project root. Inspect `.nostdb/settings.json`, the
   configured `*.nostdb`, `.nost` modules below `.nostdb/`, linked child
   projects, and Git changes. Preserve unrelated work.
2. Initialize NDB-only by default. Enable `source.enabled` and synchronize
   before creating or directly editing `.nost`.
3. Resolve the exact configured CLI before semantic work:

```bash
python3 <skill-root>/scripts/nostdb_core.py resolve \
  --src <src> --json
```

4. Use the selected task reference. Database queries write the configured
   `*.nostdb` first. For direct source work, preserve Stable Module IDs, operate
   on complete `.nost` files through the guarded workflow, and treat Core
   diagnostics as authoritative.
5. After a source change, invoke the CLI only through the same wrapper:

```bash
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  format --file <owner.nost> --project <src> --check
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  sync --project <src> --format json
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  doctor --project <src> --format json
```

6. Run the `update` action after project-structure changes so nested roots and
   the parent synchronize in dependency order.
7. Report changed source and settings files, commands, warnings, unresolved
   references, constraint failures, links, and source conflicts.

`--src` is the Skill-wrapper source-root option. Arguments after `--` belong to
the native CLI, whose local-project option is `--project`.

Use `nostdb-visualize` when the requested outcome is a diagram or visualization
dataset. Never open, generate, patch, or interpret `*.nostdb` bytes; only the
resolved CLI may create or update a database.
