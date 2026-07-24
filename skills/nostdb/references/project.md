# Project and Core configuration

## Managed project layout

Treat `.nostdb/` as the only managed project directory. `.nostdb` is also the
database filename suffix; it is never a complete database filename.

```text
<project>/
└── .nostdb/
    ├── settings.json
    ├── root.nostdb
    ├── root.nost
    └── modules/
        └── *.nost
```

`root.nostdb` is the default. `database.root` may select another filename
ending in `.nostdb`; it may not contain a directory component. Source paths in
settings are relative to `.nostdb/`.

Initialize once:

```bash
python3 <skill-root>/scripts/nostdb_skill.py init \
  --src <src> --core-version 0.0.3 \
  --core-provider installed
```

Initialization refuses a nonempty directory. After inspecting an existing
project and confirming it is the intended destination, add
`--allow-nonempty`. An existing `.nostdb/` is never adopted or replaced.

The wrapper invokes native `nostdb init`, then adds Agent provider metadata:

```json
{
  "version": 1,
  "database": {
    "root": "root.nostdb",
    "links": []
  },
  "source": {
    "version": 1,
    "enabled": false
  },
  "skills": {
    "core_provider": "installed",
    "core_version": "0.0.3"
  }
}
```

`skills.core_binary` is project-owned metadata and never automatic execution
authority. An explicit wrapper `--binary`, `NOSTDB_BIN`, then the `nostdb`
command are checked in that order. The ordinary command is executed directly
without retaining its resolved path, and every selection requires exact
`nostdb --version` equality.

To expose canonical source:

```bash
python3 <skill-root>/scripts/nostdb_project.py configure \
  --src <src> --source-enabled true
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  sync --project <src> --format json
```

Sync creates a single `.nost` whose basename matches the configured database
(`.nostdb/root.nost` for `.nostdb/root.nostdb`) or
`.nostdb/modules/*.nost` for multiple Stable Module IDs. Disabling
`source.enabled` and syncing removes only configured generated sources.

## Nested project links

Run project discovery after adding, removing, or moving nested projects:

```bash
python3 <skill-root>/scripts/nostdb_skill.py update --src <src>
```

Discovery records each nearest nested project as a deterministic
`database.links` entry containing its parent-relative project path and
configured database filename. It refreshes nested settings first, then native
`nostdb update` synchronizes child databases before the parent. Discovery does
not cross symlinks, VCS metadata, dependency caches, or build outputs.

## Removal

Remove all nested project-local NostDB artifacts in one operation:

```bash
python3 <skill-root>/scripts/nostdb_skill.py remove --src <src>
```

The removal plan contains only `.nostdb/` directories below the confirmed
project root. It preserves unrelated files and parent directories. Use
`--dry-run` to inspect exact targets. Removal requires a regular root
`.nostdb/settings.json`, rejects filesystem root/home and symlink boundaries,
and refuses a database whose ownership lock is active.
