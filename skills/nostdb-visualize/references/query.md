# Read-only visualization query boundary

The visualization wrapper exposes only query, inspect, stats, schema, unresolved, and check against one existing .ndb. It rejects synchronization, source commands, remote or database administration, interactive input, query files, and arbitrary CLI passthrough.

For a standalone NDB-only database, no nostdb.toml is needed. Explicitly authorize the reviewed binary and database:

    python3 <skill-root>/scripts/nostdb_core.py resolve \
      --binary /absolute/path/to/nostdb --database /absolute/path/to/graph.ndb --json
    python3 <skill-root>/scripts/nostdb_core.py run \
      --binary /absolute/path/to/nostdb --database /absolute/path/to/graph.ndb -- \
      query --read-only \
      'MATCH (n) RETURN id(n) AS internal_id, n ORDER BY internal_id LIMIT 101' \
      --format json

For a configured project, --project may select the pinned provider, but --database remains explicit:

    python3 <skill-root>/scripts/nostdb_core.py run \
      --project <project> --database <project>/<skills.database> -- \
      query --read-only \
      'MATCH (n) RETURN id(n) AS internal_id, n ORDER BY internal_id LIMIT 101' \
      --format json

The wrapper requires one inline query input and forwards it unchanged with --read-only. The CLI and Rust Core parse and classify every statement and reject writes before synchronization or database creation. The wrapper never forwards --project, so a visualization query cannot trigger implicit Source Mode synchronization.

Start with a declared display bound such as 100, query in deterministic order, and fetch one extra row or run a count query to detect truncation. Narrow topology traversals before raising the bound.

Inspection uses the same explicit database boundary:

    python3 <skill-root>/scripts/nostdb_core.py run \
      --binary /absolute/path/to/nostdb --database /absolute/path/to/graph.ndb -- \
      inspect --format json
    python3 <skill-root>/scripts/nostdb_core.py run \
      --binary /absolute/path/to/nostdb --database /absolute/path/to/graph.ndb -- \
      unresolved --format json

source_managed: true means the database was materialized from Source Mode; visualization still reads the existing .ndb without synchronizing it. Use RETURN DISTINCT id(n) AS internal_id, ... ORDER BY ..., internal_id when a database-local tie-breaker is required. Internal IDs are query-visible correlation keys, not permanent external identity.
