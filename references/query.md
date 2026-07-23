# Query boundary

Use the public openCypher-compatible subset only. Unsupported syntax must remain an explicit diagnostic.

Read-only exploration commonly uses `MATCH`, `OPTIONAL MATCH`, `WHERE`, `RETURN`, `WITH`, `DISTINCT`, `ORDER BY`, `SKIP`, `LIMIT`, `UNWIND`, and `EXPLAIN`. `id(node)` exposes the query-visible internal ID for deterministic ordering within the current database; it is not permanent external identity. Result order is undefined without `ORDER BY`.

Prefer machine output:

```bash
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  query 'MATCH (n) RETURN n LIMIT 100' \
  --project <src> --format json
```

Inspect the exact administration surfaces without entering the REPL:

```bash
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  schema --database <src>/.nostdb --format json
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  unresolved --database <src>/.nostdb --format json
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  imports --project <src> --format json
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  warnings --project <src> --format json
```

Start with `LIMIT 100` or lower. Narrow topology traversals before raising it.
Project query writes commit to the root `.nostdb`; when `nost` is enabled, the
CLI synchronizes canonical human-readable source after the commit.

Detect authority mode exactly:

```bash
python3 <skill-root>/scripts/nostdb_core.py run --src <src> -- \
  inspect --database <src>/.nostdb --format json
```

`nost: true` means a human-readable-source synchronization baseline exists; it
does not make `.nostdb` read-only. `false` is the default NDB-only project.
Use `RETURN DISTINCT id(n) AS internal_id, ... ORDER BY ..., internal_id` when a
stable database-local tie-breaker is required.

Use `stats`, `check`, and `doctor` for database/project health.
