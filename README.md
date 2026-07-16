# nostos-skills

Shared portable skill structure for Codex and Claude, licensed under Apache-2.0.

Stage 0 creates the six canonical skill directories and empty adapter/reference/script structures. Every `SKILL.md` is an explicit nonfunctional placeholder. Ingestion, schema work, exploration, visualization, source editing, adapter installation, and Core invocation are deferred to Stage 9.

Skills may eventually propose and write canonical `.nostos` through supported workflows. They must never write `.ndb` directly or implement an independent parser or binary writer.

## Structure

- `skills/`: canonical portable skill definitions
- `adapters/codex/`: deferred Codex adapter
- `adapters/claude/`: deferred Claude adapter
- `references/`: deferred shared references
- `scripts/`: deferred deterministic helper scripts

## License

Licensed under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
