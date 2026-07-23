# Agent instructions for skills

Follow the Root `AGENTS.md` when working in the multi-repository workspace.

- Canonical workflows live in independently installable `skills/*` directories and are distributed through the skills.sh-compatible CLI.
- Every public Skill must bundle all runtime references and scripts below its own directory. Do not use a relative path that escapes the Skill, depend on the repository checkout or current working directory, assume an agent-specific parent, or require another NostDB Skill.
- NostDB-maintained Codex/Claude adapters are not part of the public installation contract.
- Skills may eventually write `.nostdb`, but they must never write `.ndb` directly.
- Do not implement a parser, storage layer, or binary writer.
- Follow the active Root Stage. Keep deterministic helpers dependency-free and route parsing, formatting, validation, synchronization, queries, and `.ndb` writes through the public CLI.
- Preserve the Apache-2.0 license assignment.
