# Document and code ingestion workflow

1. Inventory only the requested inputs and inspect existing Schemas and Stable Module mappings. Do not infer ownership from a path alone.
2. Propose entity identity, deduplication keys, Schemas, and relationship direction before writing. Keep uncertain facts explicit and never invent missing evidence.
3. Generate a deterministic provenance comment for every source location with `nostos_provenance.py`; insert it immediately before the supported declaration. Use a stable page, section, heading, symbol, or line locator.
4. Before installing a candidate, rerun the provenance helper with the recorded `--expected-sha256`. Discard and review the extraction again if the input changed.
5. Use `imports` only to map module paths to Stable Module IDs; it does not establish writability. Require one explicit writable owner after reading its complete source and direct imports.
6. Preserve comments, produce a complete candidate, canonicalize it through the pinned CLI, and install it with the hash-guarded `nostos_source.py` workflow.
7. Synchronize, inspect `warnings` and `unresolved`, and review the source diff before accepting the result.

Never write `.ndb`; synchronization belongs exclusively to the pinned CLI.
