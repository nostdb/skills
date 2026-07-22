# Project and Core configuration

## Layout selection

- `centralized`: use for a graph maintained together under `.nostos/`.
- `colocated`: use when graph modules follow the code or documents they describe.
- `single`: use only for a genuinely small graph that benefits from one source file.

Initialize once:

```bash
python3 <skill-root>/scripts/nostos_skill.py init \
  --project <project> --layout centralized --core-version 0.0.1 \
  --core-provider auto
```

Initialization refuses a nonempty directory. After inspecting an existing code/document project and confirming it is the intended destination, add `--allow-nonempty`; existing `nostos.toml` and the selected source target are still never replaced.

The helper creates one canonical source entry, a nonzero Stable Module ID, and these independent pins in `nostos.toml`:

```toml
config_version = 1
language_version = 1

[source]
layout = "centralized"
entry = ".nostos/graph.nostos"

[modules]
".nostos/graph.nostos" = "<stable-module-id>"

[skills]
core_provider = "auto"
core_version = "0.0.1"
database = "graph.ndb"
```

`[skills] core_binary` may contain an absolute path or a project-relative path, but it is project-owned metadata and is never automatic execution authority. An explicit wrapper `--binary`, `NOSTOS_BIN`, then the user's `PATH` are checked in that order. When metadata is present without an explicit override, the wrapper warns that it is ignored; after reviewing the binary, authorize it with `--binary PATH` or `NOSTOS_BIN=PATH`. `skills.database` is the normalized project-relative authoritative artifact passed only to the CLI. The wrapper requires exact `nostos --version` equality and exits with a clear diagnostic on mismatch. `installed` forbids npx fallback, `npx` always uses the exact official package version, and `auto` falls back only when no native candidate exists. A missing `core_provider` retains installed-only behavior for existing projects. For an existing project missing a required Skill key, ask the user and persist it with `configure --core-version ... --core-provider ... --database ...` before continuing.

Persist a user-approved selection without moving files:

```bash
python3 <skill-root>/scripts/nostos_project.py configure \
  --project <project> --layout colocated --core-version 0.0.1 \
  --core-provider auto
```

Changing `source.layout` records organization intent; it does not migrate modules. Moving modules requires an explicit multi-file plan that preserves every Stable Module ID and verifies the semantic graph hash.
