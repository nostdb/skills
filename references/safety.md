# Safety and authority

- In Source Mode, `.nostos` is authoritative and synchronization is one-way to `.ndb`.
- In NDB-only and Server Modes, `.ndb` is authoritative. A logical source export is not bidirectional synchronization.
- Never open, create, patch, copy as a mutation, or decode `.ndb` in a Skill or helper. Invoke the pinned public `nostos` CLI and let Core own all storage behavior.
- Never store a file path as permanent entity or Schema identity. Preserve Stable Module IDs from `nostos.toml`.
- Never create an Edge with a missing endpoint. Let Core create or resolve Placeholder Nodes for missing imports.
- Do not edit imported read-only modules automatically.
- Before editing a `.nostos` file, read the whole file and preserve its comments. Hash the owner with `nostos_source.py hash --file <owner.nostos>`. Rewrite the complete file as a separate candidate, format that candidate through the pinned wrapper, capture its stdout as `<canonical-candidate>`, and install it with `nostos_source.py install --file <owner.nostos> --from <canonical-candidate> --expected-sha256 <original-hash>`. Run the exact owner-file format check below after installation.
- Inspect Git changes and content again before replacement. The guarded helper uses an exclusive cooperative lock with PID/host metadata, inode/content checks immediately before replacement, and restoration if an in-place writer races the replacement. Stop on any conflict diagnostic; never overwrite the other change. After a crash, `nostos_source.py unlock --file <owner.nostos>` removes only a same-host lock whose recorded PID is no longer alive.
- Use an explicit migration plan for changes spanning multiple source files.
- Treat parser, Constraint, integrity, and unsupported-query diagnostics as authoritative. Never silently reinterpret invalid syntax.

```bash
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  format --file <candidate.nostos> --project <project>
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  format --file <owner.nostos> --project <project> --check
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  sync --project <project> --database <project>/<skills.database> --format json
python3 <skill-root>/../../scripts/nostos_core.py run --project <project> -- \
  check --database <project>/<skills.database> --format json
```

The first command emits canonical source to stdout and never mutates the input. Capture that complete stdout as the candidate; do not use an unpinned `nostos` executable.
