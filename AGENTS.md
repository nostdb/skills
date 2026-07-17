# Agent instructions for nostos-skills

Follow the Root `AGENTS.md` when working in the multi-repository workspace.

- Canonical workflows live in portable `skills/*/SKILL.md` files; platform adapters must reference rather than fork them.
- Skills may eventually write `.nostos`, but they must never write `.ndb` directly.
- Do not implement a parser, storage layer, or binary writer.
- Follow the active Root Stage. Keep deterministic helpers dependency-free and route parsing, formatting, validation, synchronization, queries, and `.ndb` writes through the public CLI.
- Preserve the Apache-2.0 license assignment.
