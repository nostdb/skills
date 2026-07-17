---
name: nostos-explore
description: Explore a NostosDB graph with bounded read-only openCypher-compatible queries and machine-readable results. Use when inspecting schemas, finding entities or neighbors, explaining a query, checking unresolved references, or answering graph questions without mutation.
---

# Explore a graph safely

Read [safety.md](../../references/safety.md) and [query.md](../../references/query.md).

1. Require the explicit project directory and use the `database` returned by `nostos_core.py resolve --json`; do not infer either from an unrelated working directory. Determine Source Mode or NDB-only mode.
2. Inspect `schema`, `warnings`, and `unresolved` state before assuming the graph is complete.
3. Clarify hop count, direction, Edge type, and entity disambiguation. If the user leaves topology open, state a one-hop/either-direction default. If the start entity is not unique, stop for a unique predicate rather than combining matches.
4. Start with a narrow read query and an explicit `LIMIT`. Use `DISTINCT` for entity sets and `id(entity)` as the final database-local `ORDER BY` tie-breaker whenever result order matters.
5. Use JSON or JSONL output for subsequent reasoning. Keep queries and raw diagnostics available for review.
6. Use `EXPLAIN` before a potentially broad traversal. Refine labels, properties, direction, and limits rather than materializing an unbounded result.
7. Correlate `id(entity)` with the `unresolved` command's `internal_id` and distinguish Placeholder/STALE entities from resolved data.

Do not issue write clauses unless the user explicitly changes the task to source editing and the orchestrator selects an owner workflow. Never access `.ndb` directly.
