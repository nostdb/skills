# Safety and authority

- In Source Mode, `.nostdb` is authoritative and synchronization is one-way to `.ndb`.
- In NDB-only and Server Modes, `.ndb` is authoritative. A logical source export is not bidirectional synchronization.
- Never open, create, patch, copy as a mutation, or decode `.ndb` in a Skill or helper. Invoke the pinned public `nostdb` CLI and let Core own all storage behavior.
- Never store a file path as permanent entity or Schema identity. Preserve Stable Module IDs from `nostdb.toml`.
- Never create an Edge with a missing endpoint. Let Core create or resolve Placeholder Nodes for missing imports.
- Do not edit imported read-only modules automatically.
- Before editing a `.nostdb` file, read the whole file and preserve its comments. Hash the owner with `nostdb_source.py hash --file <owner.nostdb>`. Rewrite the complete file as a separate candidate, format that candidate through the pinned wrapper, capture its stdout as `<canonical-candidate>`, and install it with `nostdb_source.py install --file <owner.nostdb> --from <canonical-candidate> --expected-sha256 <original-hash>`. Run the exact owner-file format check below after installation.
- Inspect Git changes and content again before replacement. The guarded helper uses an exclusive cooperative lock with PID/host metadata, an exclusively created and fsynced same-directory temporary file, and a fresh descriptor/inode/content check immediately before atomic replacement. It restores external content if an in-place writer races the replacement. Stop on any conflict diagnostic; never overwrite the other change. After a crash, `nostdb_source.py unlock --file <owner.nostdb>` removes only a same-host lock whose recorded PID is no longer alive.
- Use an explicit migration plan for changes spanning multiple source files.
- Treat parser, Constraint, integrity, and unsupported-query diagnostics as authoritative. Never silently reinterpret invalid syntax.

```bash
python3 <skill-root>/scripts/nostdb_core.py run --project <project> -- \
  format --file <candidate.nostdb> --project <project>
python3 <skill-root>/scripts/nostdb_core.py run --project <project> -- \
  format --file <owner.nostdb> --project <project> --check
python3 <skill-root>/scripts/nostdb_core.py run --project <project> -- \
  sync --project <project> --database <project>/<skills.database> --format json
python3 <skill-root>/scripts/nostdb_core.py run --project <project> -- \
  check --database <project>/<skills.database> --format json
```

The first command emits canonical source to stdout and never mutates the input. Capture that complete stdout as the candidate; do not use an unpinned `nostdb` executable.
