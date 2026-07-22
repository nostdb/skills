# NostosDB Skills

Portable Codex and Claude workflows for NostosDB, licensed under Apache-2.0.

Public-preview source only: no supported Skill package, registry publication, model guarantee, or external contribution intake exists. Read [PREVIEW.md](PREVIEW.md), [SECURITY.md](SECURITY.md), and [CLA status](CLA.md).

Start with the Root [user guide](https://github.com/nostosdb/nostosdb/blob/main/docs/USER_GUIDE.md) for project setup, example requests, provider selection, updates, and troubleshooting.

Two canonical Agent Skills provide the public surface:

- `nostos` is the default entry point for `help`, guarded project `init`, deterministic Core commands, Schema evolution, ingestion, and exploration.
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

After the agent activates the Skill, `nostos help` returns the supported action summary without requiring a project, and `nostos init` collects the project/layout inputs and invokes the bundled guarded initializer. These are Agent Skill actions, not additional subcommands of the native `nostos` CLI.

## Source-preview quickstart

The CLI packages are not published yet, so the working preview path uses an explicitly authorized source-built binary. From this repository with `nostosdb-cli` and `nostosdb-core` checked out as siblings:

```bash
cargo build --manifest-path ../nostosdb-cli/Cargo.toml --locked
export NOSTOS_BIN="$PWD/../nostosdb-cli/target/debug/nostos"
export NOSTOS_PROJECT="$PWD/../nostos-preview"
python3 skills/nostos/scripts/nostos_skill.py init \
  --project "$NOSTOS_PROJECT" --layout centralized --core-provider installed \
  --core-binary "$NOSTOS_BIN"
python3 skills/nostos/scripts/nostos_core.py resolve \
  --project "$NOSTOS_PROJECT" --json
```

`--core-binary` records the reviewed path as project metadata. Because `nostos.toml` is project-controlled input, that value is never executed automatically; keep `NOSTOS_BIN` set for the agent session or pass `--binary PATH` to each wrapper invocation. Otherwise resolution uses `nostos` from the user's `PATH`.

## CLI provider

The initializer supports `auto`, `installed`, and `npx` provider policies. Use `installed` for the current source preview. `auto` first selects an explicitly authorized or `PATH`-installed `nostos` whose version exactly matches `skills.core_version`; if none exists, it runs the exact `@nostosdb/cli@skills.core_version` package through `npx`. `installed` forbids that network fallback, while `npx` requires the pinned zero-install provider.

Skill installation and CLI execution are separate uses of `npx`:

- `npx skills add ...` downloads an Agent Skill from this GitHub repository.
- `npx --package=@nostosdb/cli@VERSION nostos ...` runs the Core-containing CLI selected by the Skill.

The `@nostosdb/cli` package is not published in the current source preview. Until publication, `auto` without an installed CLI and the `npx` policy fail explicitly. Preview evaluation must use the installed-provider workflow above with an exactly matching source-built `nostos` binary. The wrapper never falls back to `latest` or a version range.

Skills may write complete canonical `.nostos` files and invoke supported CLI commands. They never parse, generate, patch, or decode `.ndb` directly.

## Verify

```bash
cargo build --manifest-path ../nostosdb-cli/Cargo.toml --locked
python3 -m py_compile scripts/*.py skills/*/scripts/*.py adapters/*/*.py tests/test_skills.py
NOSTOS_TEST_BIN="$PWD/../nostosdb-cli/target/debug/nostos" \
  python3 -m unittest discover -s tests -v
python3 scripts/verify_skills.py --format-check
python3 scripts/verify_skills.py
```

The explicit `NOSTOS_TEST_BIN` assignment makes the real CLI integration mandatory. Without it, the suite uses an already-built sibling development binary when available and otherwise skips that integration. The test compares canonical source hashes, logical database checksums, graph counts, diagnostics, and exit behavior.

## License

Licensed under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
