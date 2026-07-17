# nostos-skills

Portable Codex and Claude workflows for NostosDB, licensed under Apache-2.0.

Six canonical Agent Skills coordinate projects, deterministic Core commands, ingestion, schema evolution, exploration, and visualization. Both platform adapters install the same Skill bytes and shared support files; only their discovery directory differs.

## Install

```bash
python3 adapters/codex/install.py --project /path/to/project
python3 adapters/claude/install.py --project /path/to/project
```

Installers refuse existing targets unless `--force` is explicit. Copy mode is the portable default; `--mode symlink` supports local development.

Initialize a project and pin the compatible CLI:

```bash
python3 scripts/nostos_project.py init \
  --project /path/to/project \
  --layout centralized \
  --core-version 0.1.0
python3 scripts/nostos_core.py resolve --project /path/to/project
```

Skills may write complete canonical `.nostos` files and invoke supported CLI commands. They never parse, generate, patch, or decode `.ndb` directly.

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
