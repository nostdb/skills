# Agent instructions for nostos-skills

Follow the Root `AGENTS.md` when working in the multi-repository workspace.

- Canonical workflows live in portable `skills/*/SKILL.md` files; platform adapters must reference rather than fork them.
- Skills may eventually write `.nostos`, but they must never write `.ndb` directly.
- Do not implement a parser, storage layer, or binary writer.
- Stage 0 files are not-yet-implemented placeholders; all skill behavior is deferred to Stage 9.
- Preserve the Apache-2.0 license assignment.
