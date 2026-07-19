# nostos-skills

Portable Codex and Claude workflows for NostosDB, licensed under Apache-2.0.

Public-preview source only: no supported Skill package, registry publication, model guarantee, or external contribution intake exists. Read [PREVIEW.md](PREVIEW.md), [SECURITY.md](SECURITY.md), and [CLA status](CLA.md).

Start with the Root [user guide](https://github.com/nostosdb/nostosdb/blob/main/docs/USER_GUIDE.md) for a runnable macOS, Windows, or Ubuntu source-preview setup, first project, example requests, updates, and troubleshooting. The guide distinguishes the installation path available now from the npm, `npx`, Homebrew, and direct-download channels that are not published yet.

Two canonical Agent Skills provide the public surface:

- `nostos` is the default entry point for project setup, deterministic Core commands, Schema evolution, ingestion, and exploration.
- `nostos-visualize` is the separate graph-representation workflow for reviewable diagrams and visualization datasets.

Users do not choose separate Core, Schema, ingestion, exploration, or orchestration Skills. Both platform adapters install exactly the same two Skill directories and shared support files; only their discovery directory differs.

## Source-preview install

The current preview requires a compatible native `nostos` 0.1.0 binary. Initialize an empty project before installing an adapter:

```bash
python3 scripts/nostos_project.py init \
  --project /path/to/project \
  --layout centralized \
  --core-version 0.1.0 \
  --core-provider installed \
  --core-binary /absolute/path/to/nostos
python3 adapters/codex/install.py --project /path/to/project
python3 scripts/nostos_core.py resolve --project /path/to/project
```

Use `adapters/claude/install.py` instead for Claude. For an inspected, existing project, add `--allow-nonempty` to initialization. Installers refuse an existing Nostos target unless `--force` is explicit. Copy mode is the portable default; `--mode symlink` is for local repository development.

Skills may write complete canonical `.nostos` files and invoke supported CLI commands. They never parse, generate, patch, or decode `.ndb` directly.

The implemented [Core provider contract](references/core-providers.md) keeps the installed CLI as the first choice and adds exact-version `npx` as an explicitly configured zero-install fallback. The `@nostosdb/cli` package is not published in the current preview, so source-preview users must select `installed`. Existing projects without `core_provider` remain installed-only.

## Verify

```bash
python3 -m py_compile scripts/*.py adapters/*/*.py tests/test_skills.py
python3 -m unittest discover -s tests -v
python3 scripts/verify_skills.py --format-check
python3 scripts/verify_skills.py
```

The end-to-end adapter test uses the sibling `nostos-cli` development binary or `NOSTOS_TEST_BIN` and compares canonical source hashes, logical database checksums, and graph counts.

## License

Licensed under Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
