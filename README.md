# NostosDB Skills

Portable Codex and Claude workflows for NostosDB, licensed under Apache-2.0.

Public-preview source only: no supported Skill package, registry publication, model guarantee, or external contribution intake exists. Read [PREVIEW.md](PREVIEW.md), [SECURITY.md](SECURITY.md), and [CLA status](CLA.md).

Start with the Root [user guide](https://github.com/nostosdb/nostosdb/blob/main/docs/USER_GUIDE.md) for project setup, example requests, provider selection, updates, and troubleshooting.

Two canonical Agent Skills provide the public surface:

- `nostos` is the default entry point for project setup, deterministic Core commands, Schema evolution, ingestion, and exploration.
- `nostos-visualize` is the separate graph-representation workflow for reviewable diagrams and visualization datasets.

Users do not choose separate Core, Schema, ingestion, exploration, or orchestration Skills. The accepted Stage 13 contract requires each Skill to contain its own references and deterministic helpers so either one can be installed and operated independently.

## Install with skills.sh

Run the skills.sh-compatible installer from the project where the agent will use NostosDB:

```bash
npx skills add nostosdb/skills --skill nostos
npx skills add nostosdb/skills --skill nostos-visualize
```

skills.sh installs each selected Skill as a complete runtime unit, including its own references and deterministic helpers.

Install only `nostos` when visualization is not needed, or only `nostos-visualize` for an existing read-only graph workflow. The installer selects Codex, Claude, another supported agent, and project/global scope interactively; its `--agent`, `--global`, and `--yes` options are available for non-interactive use. NostosDB does not require a custom agent adapter.

The downloaded Skill directory does not require this repository checkout, a sibling `references/` or `scripts/` directory, the other NostosDB Skill, a particular agent-specific parent path, or a particular current working directory.

## CLI provider

New projects use `core_provider = "auto"`. The Skill first selects an installed `nostos` whose version exactly matches `skills.core_version`; if none exists, it runs the exact `@nostosdb/cli@skills.core_version` package through `npx` without a global CLI installation. Set `core_provider = "installed"` when network fallback must be forbidden, or `core_provider = "npx"` to require the pinned zero-install provider.

Skill installation and CLI execution are separate uses of `npx`:

- `npx skills add ...` downloads an Agent Skill from this GitHub repository.
- `npx --package=@nostosdb/cli@VERSION nostos ...` runs the Core-containing CLI selected by the Skill.

The `@nostosdb/cli` package is not published in the current source preview. Until publication, the npx provider fails explicitly and preview evaluation must provide an exactly matching source-built `nostos` binary. It never falls back to `latest` or a version range.

Skills may write complete canonical `.nostos` files and invoke supported CLI commands. They never parse, generate, patch, or decode `.ndb` directly.

## Verify

```bash
python3 -m py_compile scripts/*.py skills/*/scripts/*.py adapters/*/*.py tests/test_skills.py
python3 -m unittest discover -s tests -v
python3 scripts/verify_skills.py --format-check
python3 scripts/verify_skills.py
```

The end-to-end isolated-install tests use the sibling `nostosdb-cli` development binary or `NOSTOS_TEST_BIN` and compare canonical source hashes, logical database checksums, graph counts, diagnostics, and exit behavior.

## License

Licensed under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
