# NostDB Skills

Portable Codex and Claude workflows for NostDB, licensed under Apache-2.0.

Public-preview source only: no supported Skill package, registry publication, model guarantee, or external contribution intake exists. Read [PREVIEW.md](PREVIEW.md), [SECURITY.md](SECURITY.md), and [CLA status](CLA.md).

Start with the Root [user guide](https://github.com/nostdb/nostdb/blob/main/docs/USER_GUIDE.md) for project setup, example requests, provider selection, updates, and troubleshooting.

Two canonical Agent Skills provide the public surface:

- `nostdb` is the default entry point for `help`, guarded NDB-only `init`,
  project-aware `update`, nested root linking, project-local `remove`,
  deterministic Core commands, Schema evolution, ingestion, and exploration.
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

After the agent activates the Skill, `nostdb help` returns the supported action
summary directly from `SKILL.md` without starting Python or requiring a
project, `nostdb init` delegates guarded project creation to the native CLI and
creates `.nostdb/settings.json` plus `.nostdb/root.nostdb` without
materializing `.nost`, `nostdb update` discovers nested projects and
synchronizes their configured databases before the parent, and `nostdb remove`
deletes recognized `.nostdb/` directories below one explicitly selected
project root. The `plugin` action discovers, installs, or temporarily runs
third-party `plugins/*` entries through `@nostdb/plugins`. Native project
creation and dependency-ordered synchronization are also available as
`nostdb init` and `nostdb update`. Static help never uses Python.

## Source-preview quickstart

For source development with an explicitly authorized binary, use this
repository with `nostdb-cli` and `nostdb-core` checked out as siblings:

```bash
cargo build --manifest-path ../nostdb-cli/Cargo.toml --locked
export NOSTDB_BIN="$PWD/../nostdb-cli/target/debug/nostdb"
export NOSTDB_SRC="$PWD/../nostdb-preview"
python3 skills/nostdb/scripts/nostdb_skill.py init \
  --src "$NOSTDB_SRC" --core-provider installed \
  --core-binary "$NOSTDB_BIN"
python3 skills/nostdb/scripts/nostdb_core.py resolve \
  --src "$NOSTDB_SRC" --json
```

`--core-binary` records the reviewed path as project metadata. Because
`.nostdb/settings.json` is project-controlled input, that value is never
executed automatically; keep `NOSTDB_BIN` set for the agent session or pass
`--binary PATH` to each wrapper invocation. Otherwise resolution uses
the `nostdb` command from the user's `PATH` without expanding it to a retained
filesystem path.

## CLI provider

The initializer supports `auto`, `installed`, and `npx` provider policies. Use
`installed` for the current source preview. `auto` first runs an explicitly
authorized binary or the `nostdb` command and requires an exact
`skills.core_version` match; if the command is unavailable, it runs the exact
official `@nostdb/cli@latest` package through `npx`. `installed` forbids
that network fallback, while `npx` requires the public-latest zero-install
provider.

Skill installation and CLI execution are separate uses of `npx`:

- `npx skills add ...` downloads an Agent Skill from this GitHub repository.
- `npx --package=@nostdb/cli@latest nostdb ...` runs the Core-containing CLI selected by the Skill.
- `npx --yes @nostdb/plugins@latest ...` discovers or runs decentralized plugins.

The wrapper validates installed CLI versions and uses only the official
`latest` dist-tag when a native command is absent.

Skills may enable `source.enabled`, write complete canonical `.nost` files
below `.nostdb/`, and invoke supported CLI commands. They never parse,
generate, patch, or decode a `*.nostdb` database directly.

Remove a Skill-managed NostDB project after reviewing the exact root and
stopping any database owner:

```bash
python3 skills/nostdb/scripts/nostdb_skill.py remove --src "$NOSTDB_SRC"
```

Add `--dry-run` to list every target without deleting it. Unrelated files in
the project root are preserved.

## Verify

```bash
cargo build --manifest-path ../nostdb-cli/Cargo.toml --locked
python3 -m py_compile scripts/*.py skills/*/scripts/*.py adapters/*/*.py tests/test_skills.py
NOSTDB_TEST_BIN="$PWD/../nostdb-cli/target/debug/nostdb" \
  python3 -m unittest discover -s tests -v
python3 scripts/verify_skills.py --format-check
python3 scripts/verify_skills.py
```

The explicit `NOSTDB_TEST_BIN` assignment makes the real CLI integration mandatory. Without it, the suite uses an already-built sibling development binary when available and otherwise skips that integration. The test compares canonical source hashes, graph generations/counts, diagnostics, and exit behavior; timestamp-dependent checksums are not cross-run equality keys.

## License

Licensed under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
