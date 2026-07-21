# Query boundary

Use the public openCypher-compatible subset only. Unsupported syntax must remain an explicit diagnostic.

Read-only exploration commonly uses `MATCH`, `OPTIONAL MATCH`, `WHERE`, `RETURN`, `WITH`, `DISTINCT`, `ORDER BY`, `SKIP`, `LIMIT`, `UNWIND`, and `EXPLAIN`. `id(node)` exposes the query-visible internal ID for deterministic ordering within the current database; it is not permanent external identity. Result order is undefined without `ORDER BY`.

Prefer machine output:

```bash
python3 <skill-root>/scripts/nostos_core.py run --project <project> -- \
  query 'MATCH (n) RETURN n LIMIT 100' \
  --project <project> --database <project>/<skills.database> --format json
```

Inspect the exact administration surfaces without entering the REPL:

```bash
python3 <skill-root>/scripts/nostos_core.py run --project <project> -- \
  schema --database <project>/<skills.database> --format json
python3 <skill-root>/scripts/nostos_core.py run --project <project> -- \
  unresolved --database <project>/<skills.database> --format json
python3 <skill-root>/scripts/nostos_core.py run --project <project> -- \
  imports --project <project> --format json
python3 <skill-root>/scripts/nostos_core.py run --project <project> -- \
  warnings --project <project> --format json
```

Start with `LIMIT 100` or lower. Narrow topology traversals before raising it. Source Mode query writes require an explicit owner Stable Module ID and the CLI's conflict-safe source workflow; do not use that path during read-only exploration or visualization.

Detect authority mode exactly:

```bash
python3 <skill-root>/scripts/nostos_core.py run --project <project> -- \
  inspect --database <project>/<skills.database> --format json
```

`source_managed: true` means Source Mode; `false` means NDB-only authority. Use `RETURN DISTINCT id(n) AS internal_id, ... ORDER BY ..., internal_id` when a stable database-local tie-breaker is required. The `unresolved` command returns the same `internal_id` for unresolved/stale Nodes, allowing exact correlation; Schema rows have a null internal ID.

Use `stats`, `check`, and `doctor` for database/project health.
