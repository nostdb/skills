---
name: nostos-ingest
description: Convert local documents or source code into reviewable NostosDB .nostos declarations with deterministic provenance. Use when extracting entities and relationships from files, incrementally ingesting a corpus, or updating graph source while retaining source hashes and locators.
---

# Ingest documents and code

1. Read [safety.md](../../references/safety.md), [project.md](../../references/project.md), [provenance.md](../../references/provenance.md), and [query.md](../../references/query.md).
2. Inventory the requested inputs and inspect existing Schemas and Stable Module mappings. Do not infer ownership from a path alone.
3. Propose entity identity, deduplication keys, Schemas, and relationship direction before writing. Keep uncertain facts explicit; do not invent missing evidence.
4. Before extracting facts, emit a deterministic provenance comment for each source location:

```bash
python3 <skill-root>/../../scripts/nostos_provenance.py \
  --project <project> --source <input> --kind document --locator <page-or-section>
```

5. Insert the comment immediately before the declaration it supports. Use `kind code` and a stable symbol or line locator for code ingestion. Before installing the candidate, rerun the helper with the recorded `--expected-sha256`; stop and review again if the input changed.
6. Use `imports` only to map module paths to Stable Module IDs; it does not declare writability. Require the user to approve one owner after reading its complete source and direct imports, and never auto-select a module imported by the owner. Preserve comments, write a complete candidate, canonicalize it with the pinned wrapper, and use the hash-guarded `nostos_source.py install` workflow from `safety.md`.
7. Use `nostos-core` to format and synchronize, then run the exact `warnings` and `unresolved` commands in [query.md](../../references/query.md). Review the source diff before accepting it.

Never write `.ndb`; synchronization belongs exclusively to the pinned CLI.
