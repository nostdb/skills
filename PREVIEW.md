# Skills preview status

The two independently installable Skills (`nostdb` and `nostdb-visualize`) are Apache-2.0 evaluation workflows, not a supported package. They are downloaded from `nostdb/skills` with the skills.sh-compatible `npx skills add` command; NostDB does not require public Codex or Claude installation adapters.

- Workflows can propose and canonically rewrite `.nost`; they never write `.nostdb`.
- Deterministic parsing, validation, sync, and query behavior belongs to the exact compatible CLI/Core version pinned by the project.
- External source content remains untrusted input; provenance is evidence, not truth or authorization.
- Each skills.sh download contains its own references and helpers and works without the repository checkout, sibling support directories, or the other Skill. Repository tests exercise isolated project/global roots and unrelated working directories.
- The official `@nostdb/cli` runtime package is not published in this preview, so zero-install CLI fallback remains a verified implementation target rather than a currently available package.
- No CLI registry distribution, hosted agent, model guarantee, or external contribution intake exists.
