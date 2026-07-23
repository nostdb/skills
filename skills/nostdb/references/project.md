# Project and Core configuration

## Fixed source layout

The Skill always initializes the `centralized` layout under `.nost/`. Layout
is not a Skill option. Do not silently migrate an existing project that uses a
different layout.

Initialize once:

```bash
python3 <skill-root>/scripts/nostdb_skill.py init \
  --src <src> --core-version 0.0.1 \
  --core-provider auto
```

Initialization refuses a nonempty directory. After inspecting an existing code/document project and confirming it is the intended destination, add `--allow-nonempty`; existing `nostdb.json` and the selected source target are still never replaced.

The helper creates one canonical source entry, a nonzero Stable Module ID, and these independent pins in `nostdb.json`:

```json
{
  "config_version": 1,
  "language_version": 1,
  "source": {"layout": "centralized", "entry": ".nost/graph.nost"},
  "modules": {".nost/graph.nost": "<stable-module-id>"},
  "skills": {
    "core_provider": "auto",
    "core_version": "0.0.1",
    "database": "graph.nostdb"
  }
}
```

`[skills] core_binary` may contain an absolute path or a project-relative path, but it is project-owned metadata and is never automatic execution authority. An explicit wrapper `--binary`, `NOSTDB_BIN`, then the user's `PATH` are checked in that order. When metadata is present without an explicit override, the wrapper warns that it is ignored; after reviewing the binary, authorize it with `--binary PATH` or `NOSTDB_BIN=PATH`. `skills.database` is the normalized project-relative authoritative artifact passed only to the CLI. The wrapper requires exact `nostdb --version` equality and exits with a clear diagnostic on mismatch. `installed` forbids npx fallback, `npx` always uses the exact official package version, and `auto` falls back only when no native candidate exists. A missing `core_provider` retains installed-only behavior for existing projects. For an existing project missing a required Skill key, ask the user and persist it with `configure --core-version ... --core-provider ... --database ...` before continuing.

Persist a user-approved selection without moving files:

```bash
python3 <skill-root>/scripts/nostdb_project.py configure \
  --src <src> --core-version 0.0.1 \
  --core-provider auto
```

The configure helper updates only the `skills` provider object. It never changes
`source.layout` or moves modules.

Remove every project-local NostDB artifact in one operation:

```bash
python3 <skill-root>/scripts/nostdb_skill.py remove --src <src>
```

The removal plan covers `nostdb.json`, the centralized `.nost/` tree, legacy
project-local `*.nost` sources, `.nostdb` databases and known sidecars, and
guarded-helper temporary or lock files. It preserves unrelated files and parent
directories. Use `--dry-run` to inspect the exact targets. Removal requires a
regular `nostdb.json`, rejects filesystem root/home and symlink boundaries, and
refuses a database whose ownership lock is active.
