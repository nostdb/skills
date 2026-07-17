---
name: nostos-core
description: Run the pinned public NostosDB CLI for canonical formatting, synchronization, validation, querying, and database inspection. Use when a workflow needs deterministic Core behavior, must locate a compatible nostos binary, or must diagnose a Core version mismatch.
---

# Use the deterministic Core boundary

Read [safety.md](../../references/safety.md), [project.md](../../references/project.md), and [query.md](../../references/query.md).

Resolve the CLI before all operations:

```bash
python3 <skill-root>/../../scripts/nostos_core.py resolve --project <project>
```

Run commands only through the same wrapper:

```bash
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  format --file <module.nostos> --project <project>
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  format --file <module.nostos> --project <project> --check
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  sync --project <project> --database <project>/<skills.database> --format json
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  doctor --project <project> --database <project>/<skills.database> --format json
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  schema --database <project>/<skills.database> --format json
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  unresolved --database <project>/<skills.database> --format json
```

For a source edit, obtain canonical text with `format --file`, replace the complete `.nostos` file using the agent's normal text-edit mechanism, then require `format --check`. Stop on parse, source-conflict, integrity, or version diagnostics; do not reinterpret them.

Never access `.ndb` with a file or database library. Pass its path only to supported `nostos` commands.
