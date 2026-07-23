# Read-only visualization safety

- Treat the configured NostDB project and database as existing authority. Do not initialize, configure, format, synchronize, or mutate them from this Skill.
- Never open, create, patch, copy as a mutation, or decode `.nostdb`. Invoke only the pinned public `nostdb` CLI through `<skill-root>/scripts/nostdb_core.py`.
- Use the wrapper's bounded `query --read-only` path or its allowlisted inspection commands only. The wrapper rejects query writes, source edits, synchronization, migrations, remote access, and administrative mutation procedures before starting the CLI.
- Preserve query-visible internal IDs separately from display labels. Never infer identity from a file path or label text.
- Treat Placeholder, STALE, unresolved Schema, parser, integrity, Constraint, and unsupported-query diagnostics as authoritative.
- Stop when the configured provider cannot resolve the exact `skills.core_version`; never weaken the version pin or substitute `latest`.

For a configured project, resolve the provider before querying:

```bash
python3 <skill-root>/scripts/nostdb_core.py resolve \
  --project <project> --json
```

For standalone NDB-only use, provide both `--binary /reviewed/nostdb` and `--database /existing/graph.nostdb`; no `nostdb.json` is required. Every run requires an explicit existing database. The wrapper never forwards a project path to the CLI, so it cannot trigger implicit synchronization.

If inspection reports `source_managed: true`, `.nost` is authoritative. The visualization workflow still reads only the existing materialized database. Otherwise `.nostdb` is authoritative. Visualization remains read-only in either mode.
