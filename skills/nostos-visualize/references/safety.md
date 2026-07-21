# Read-only visualization safety

- Treat the configured NostosDB project and database as existing authority. Do not initialize, configure, format, synchronize, or mutate them from this Skill.
- Never open, create, patch, copy as a mutation, or decode `.ndb`. Invoke only the pinned public `nostos` CLI through `<skill-root>/scripts/nostos_core.py`.
- Use bounded read-only queries and inspection commands only. Do not use query writes, source edits, migrations, or administrative mutation procedures.
- Preserve query-visible internal IDs separately from display labels. Never infer identity from a file path or label text.
- Treat Placeholder, STALE, unresolved Schema, parser, integrity, Constraint, and unsupported-query diagnostics as authoritative.
- Stop when the configured provider cannot resolve the exact `skills.core_version`; never weaken the version pin or substitute `latest`.

Resolve the provider before querying:

```bash
python3 <skill-root>/scripts/nostos_core.py resolve \
  --project <project> --json
```

If inspection reports `source_managed: true`, `.nostos` is authoritative. Otherwise `.ndb` is authoritative. Visualization remains read-only in either mode.
