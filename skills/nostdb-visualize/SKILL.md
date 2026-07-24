---
name: nostdb-visualize
description: Build reviewable graph diagrams or visualization datasets from bounded NostDB query results. Use when showing topology, neighborhoods, paths, schema relationships, unresolved entities, or producing Mermaid, DOT, or JSON visualization data.
---

# Visualize bounded graph results

Read [safety.md](references/safety.md), [query.md](references/query.md), and [core-providers.md](references/core-providers.md).

1. Define the visual question, maximum nodes/edges, direction semantics, and output format before querying.
2. Use the pinned wrapper described in [query.md](references/query.md), an explicit existing database, and the required `query --read-only` marker to run one bounded query with deterministic aliases and `ORDER BY` where presentation order matters. Never bypass the wrapper with the native CLI.
3. Transform only returned data. Preserve internal IDs separately from display labels and do not merge entities by label text.
4. Render directed, directionless, and bidirectional Edges distinctly. Mark Placeholder, STALE, and unresolved Schema state visibly.
5. Include the query, limits, omissions, and unresolved-state legend with the visualization.
6. If the result exceeds the declared bound, narrow the query; do not silently drop arbitrary rows.

Visualization is read-only. Never derive or modify `*.nostdb` bytes and never
treat a diagram as graph authority.
