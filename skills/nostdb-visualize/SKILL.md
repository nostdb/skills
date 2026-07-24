---
name: nostdb-visualize
description: Open scalable WebGPU relationship graphs through the installed nostdb-visualize plugin or build bounded static visualization datasets. Use when exploring topology, neighborhoods, paths, schema relationships, unresolved entities, or producing Mermaid, DOT, or JSON visualization data.
---

# Visualize NostDB graphs

Read [safety.md](references/safety.md), [plugin.md](references/plugin.md), and
[query.md](references/query.md).

For the default interactive graph:

1. Require one initialized project and choose project or global plugin scope.
2. Inspect the installed plugin list. If `nostdb-visualize` is missing, review
   the exact `nostdb/plugins@nostdb-visualize` source, resolved commit, digest,
   manifest, and permissions before installing it. Never run an uninstalled
   plugin.
3. Run the installed plugin as described in
   [plugin.md](references/plugin.md). Use `open` unless the user asks for a
   server URL only. Pass explicit node and edge limits when the requested scope
   is narrower than the defaults.
4. Report the selected project/global scope and any node or relationship limit
   reached. Do not claim that the visualization is graph authority.

The plugin renders dot-shaped nodes with name-only labels. Its WebGPU force
layout makes repeated/direct relationships pull nodes closer and uses sampled
repulsion to separate unrelated nodes. Dense labels are collision-culled and
appear progressively as the user zooms.

When the user explicitly requests Mermaid, DOT, JSON, or a standalone
NDB-only database without a project, use the existing bounded read-only wrapper
in [query.md](references/query.md) and
[core-providers.md](references/core-providers.md). Never bypass the wrapper
with the native CLI.

Visualization is read-only. Never derive or modify `*.nostdb` bytes.
