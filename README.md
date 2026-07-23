# NostDB Skills

Portable Codex and Claude workflows for NostDB, licensed under Apache-2.0.

Public-preview source only: no supported Skill package, registry publication, model guarantee, or external contribution intake exists. Read [PREVIEW.md](PREVIEW.md), [SECURITY.md](SECURITY.md), and [CLA status](CLA.md).

Start with the Root [user guide](https://github.com/nostdb/nostdb/blob/main/docs/USER_GUIDE.md) for project setup, example requests, provider selection, updates, and troubleshooting.

Two canonical Agent Skills provide the public surface:

- `nostdb` is the default entry point for `help`, guarded project `init`, deterministic Core commands, Schema evolution, ingestion, and exploration.
- `nostdb-visualize` is the separate graph-representation workflow for reviewable diagrams and visualization datasets.

Users do not choose separate Core, Schema, ingestion, exploration, or orchestration Skills. The accepted Stage 13 contract requires each Skill to contain its own references and deterministic helpers so either one can be installed and operated independently.

## Install with skills.sh

Run the skills.sh-compatible installer from the project where the agent will use NostDB:

```bash
npx skills add nostdb/skills --skill nostdb
npx skills add nostdb/skills --skill nostdb-visualize
```

skills.sh installs each selected Skill as a complete runtime unit, including its own references and deterministic helpers.

Install only `nostdb` when visualization is not needed, or only `nostdb-visualize` for an existing read-only graph workflow. The installer selects Codex, Claude, another supported agent, and project/global scope interactively; its `--agent`, `--global`, and `--yes` options are available for non-interactive use. NostDB does not require a custom agent adapter.

The downloaded Skill directory does not require this repository checkout, a sibling `references/` or `scripts/` directory, the other NostDB Skill, a particular agent-specific parent path, or a particular current working directory.

After the agent activates the Skill, `nostdb help` returns the supported action summary without requiring a project, and `nostdb init` collects the project/layout inputs and invokes the bundled guarded initializer. These are Agent Skill actions, not additional subcommands of the native `nostdb` CLI.

## Source-preview quickstart

The CLI packages are not published yet, so the working preview path uses an explicitly authorized source-built binary. From this repository with `nostdb-cli` and `nostdb-core` checked out as siblings:

```bash
cargo build --manifest-path ../nostdb-cli/Cargo.toml --locked
export NOSTDB_BIN="$PWD/../nostdb-cli/target/debug/nostdb"
export NOSTDB_PROJECT="$PWD/../nostdb-preview"
python3 skills/nostdb/scripts/nostdb_skill.py init \
  --project "$NOSTDB_PROJECT" --layout centralized --core-provider installed \
  --core-binary "$NOSTDB_BIN"
python3 skills/nostdb/scripts/nostdb_core.py resolve \
  --project "$NOSTDB_PROJECT" --json
```

`--core-binary` records the reviewed path as project metadata. Because `nostdb.toml` is project-controlled input, that value is never executed automatically; keep `NOSTDB_BIN` set for the agent session or pass `--binary PATH` to each wrapper invocation. Otherwise resolution uses `nostdb` from the user's `PATH`.

## CLI provider

The initializer supports `auto`, `installed`, and `npx` provider policies. Use `installed` for the current source preview. `auto` first selects an explicitly authorized or `PATH`-installed `nostdb` whose version exactly matches `skills.core_version`; if none exists, it runs the exact `@nostdb/cli@skills.core_version` package through `npx`. `installed` forbids that network fallback, while `npx` requires the pinned zero-install provider.

Skill installation and CLI execution are separate uses of `npx`:

- `npx skills add ...` downloads an Agent Skill from this GitHub repository.
- `npx --package=@nostdb/cli@VERSION nostdb ...` runs the Core-containing CLI selected by the Skill.

The `@nostdb/cli` package is not published in the current source preview. Until publication, `auto` without an installed CLI and the `npx` policy fail explicitly. Preview evaluation must use the installed-provider workflow above with an exactly matching source-built `nostdb` binary. The wrapper never falls back to `latest` or a version range.

Skills may write complete canonical `.nostdb` files and invoke supported CLI commands. They never parse, generate, patch, or decode `.ndb` directly.

## Verify

```bash
cargo build --manifest-path ../nostdb-cli/Cargo.toml --locked
python3 -m py_compile scripts/*.py skills/*/scripts/*.py adapters/*/*.py tests/test_skills.py
NOSTDB_TEST_BIN="$PWD/../nostdb-cli/target/debug/nostdb" \
  python3 -m unittest discover -s tests -v
python3 scripts/verify_skills.py --format-check
python3 scripts/verify_skills.py
```

The explicit `NOSTDB_TEST_BIN` assignment makes the real CLI integration mandatory. Without it, the suite uses an already-built sibling development binary when available and otherwise skips that integration. The test compares canonical source hashes, logical database checksums, graph counts, diagnostics, and exit behavior.

## License

Licensed under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
