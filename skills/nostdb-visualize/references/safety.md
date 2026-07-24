# Read-only visualization safety

- Treat the configured NostDB project and database as existing authority. Do not initialize, configure, format, synchronize, or mutate them from this Skill.
- For the default interactive graph, execute only an installed
  `nostdb-visualize` plugin after reviewing its source, immutable provenance,
  and declared permissions. The plugin is unsandboxed third-party code despite
  being maintained in `nostdb/plugins`.
- The plugin server must remain bound to `127.0.0.1` with its random private
  path. Do not expose it on a LAN or public interface.
- Never open, create, patch, copy as a mutation, or decode `*.nostdb`. Invoke
  the installed visualization plugin for interactive graphs or the pinned
  public `nostdb` CLI through `<skill-root>/scripts/nostdb_core.py` for static
  output.
- Use the wrapper's bounded `query --read-only` path or its allowlisted inspection commands only. The wrapper rejects query writes, source edits, synchronization, migrations, remote access, and administrative mutation procedures before starting the CLI.
- Preserve query-visible internal IDs separately from display labels. Never infer identity from a file path or label text.
- Treat Placeholder, STALE, unresolved Schema, parser, integrity, Constraint, and unsupported-query diagnostics as authoritative.
- Stop when the configured provider cannot resolve the exact `skills.core_version`; never weaken the version pin or substitute `latest`.

For a configured project using the interactive graph, follow
[plugin.md](plugin.md). For a static query, resolve the provider before
querying:

```bash
python3 <skill-root>/scripts/nostdb_core.py resolve \
  --src <project> --json
```

For standalone NDB-only use, provide both `--binary /reviewed/nostdb` and
`--database /existing/graph.nostdb`; project settings are not required. Every
run requires an explicit existing database. The wrapper never forwards a
project path to the CLI, so it cannot trigger implicit synchronization.

If inspection reports `source_enabled: true`, a human-readable-source synchronization
baseline exists. Neither representation is chosen without the
project reconciliation rules. The visualization workflow still reads only the
existing `*.nostdb` and remains read-only.
