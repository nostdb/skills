# Project and Core configuration

## Default NDB-only project

The Skill always creates the root `.nostdb`; source is hidden by default. Do
not create `.nost` until top-level `nost` is enabled.

Initialize once:

```bash
python3 <skill-root>/scripts/nostdb_skill.py init \
  --src <src> --core-version 0.0.2 \
  --core-provider auto
```

Initialization refuses a nonempty directory. After inspecting an existing
code/document project and confirming it is the intended destination, add
`--allow-nonempty`; existing `nostdb.json` and the root `.nostdb` are never
replaced.

The wrapper resolves the pinned provider and invokes native
`nostdb init --project <src>` when that CLI supports it. The CLI creates the
base configuration and database; the wrapper then adds Agent-specific provider
metadata. The published Core `0.0.2` predates native `init`, so the wrapper
retains a compatibility path that creates the same guarded configuration
in-process and invokes native `sync`:

```json
{
  "nostdb": 1,
  "root": ".nostdb",
  "nost": false,
  "skills": {
    "core_provider": "auto",
    "core_version": "0.0.2"
  }
}
```

`skills.core_binary` may contain an absolute path or a project-relative path,
but it is project-owned metadata and is never automatic execution authority.
An explicit wrapper `--binary`, `NOSTDB_BIN`, then the user's `PATH` are checked
in that order. The top-level `root` is always the project-local `.nostdb`. The
wrapper requires exact `nostdb --version` equality.
`installed` forbids npx fallback, `npx` always uses the exact official package
version, and `auto` falls back only when no native candidate exists.

To expose canonical source for direct editing:

```bash
python3 <skill-root>/scripts/nostdb_project.py configure \
  --src <src> --nost true
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  sync --project <src> --format json
```

The sync creates `.nost/graph.nost` for one module or `.nost/modules/*.nost`
for multiple Stable Module IDs. Setting `nost` back to `false` and syncing
removes only those configured generated sources.

Persist a user-approved selection without moving files:

```bash
python3 <skill-root>/scripts/nostdb_project.py configure \
  --src <src> --core-version 0.0.2 \
  --core-provider auto
```

The configure helper can update provider metadata or top-level `nost`. The
fixed `root` and source paths/Stable Module mappings remain Core-managed.

Remove every project-local NostDB artifact in one operation:

```bash
python3 <skill-root>/scripts/nostdb_skill.py remove --src <src>
```

The removal plan covers `nostdb.json`, the default `.nost/` tree, `.nostdb`
databases and known sidecars, and guarded-helper temporary or lock files. It
preserves unrelated files, unmanaged `.nost` files outside `.nost/`, and parent
directories. Use `--dry-run` to inspect the exact targets. Removal requires a
regular `nostdb.json`, rejects filesystem root/home and symlink boundaries, and
refuses a database whose ownership lock is active.
