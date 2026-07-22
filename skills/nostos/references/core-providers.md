# Installed and zero-install Core providers

Status: implemented provider contract.

Skills never reimplement Core behavior. Every format, sync, validation, query, inspection, and `.ndb` operation delegates to the official `nostos` CLI. That executable already contains the Rust Core implementation, so no separate Core package or service is installed.

## Provider contract

The wrapper represents execution as an argument vector rather than assuming one executable path:

```text
native: ["/absolute/path/to/nostos"]
npx:    ["npx", "--yes", "--package=@nostosdb/cli@VERSION", "nostos"]
```

It appends the same CLI arguments to either vector and invokes it without a shell. Stdout, stderr, signals, and exit status remain CLI-owned.

Native resolution order is an explicit `--binary`, `NOSTOS_BIN`, then `nostos` on the user's `PATH`. Each candidate must be a file and must return exactly `nostos <skills.core_version>` from `--version`. An existing wrong-version candidate is an error, not permission to hide the mismatch with npx.

`skills.core_binary` is project-owned metadata, not execution authority. The initializer may record an absolute or project-relative path so humans and tooling can see which installed binary was selected, but the wrapper never executes that value automatically. When the key is present without `--binary` or `NOSTOS_BIN`, resolution prints an actionable warning and continues with `PATH`. This prevents merely opening an unreviewed project from executing a project-selected program. After reviewing a binary, authorize it for the current invocation with `--binary PATH` or for the current environment with `NOSTOS_BIN=PATH`.

The project policy is:

```toml
[skills]
core_version = "0.0.1"
database = "graph.ndb"
core_provider = "auto" # auto | installed | npx
```

- `installed`: use native resolution only and never initiate a network fallback.
- `npx`: invoke the exact official package version recorded by `core_version`.
- `auto`: prefer a compatible native binary and otherwise use the pinned npx provider.
- missing: preserve current installed-only behavior for existing projects until explicit configuration or migration.

The package scope and name are fixed by implementation, not accepted from source content, prompts, or arbitrary project input. The wrapper never uses `latest` or a version range. npx requires the command plus network access or a usable npm cache; failure reports the pinned version and installation alternatives without weakening the version check.

The `@nostosdb/cli` package is not published during the current source preview. Build the sibling CLI repository, select `core_provider = "installed"`, and export its reviewed absolute path through `NOSTOS_BIN` before invoking the wrapper. A matching `core_binary` value may also be recorded during initialization, but remains non-authoritative metadata:

```bash
cargo build --manifest-path ../nostosdb-cli/Cargo.toml --locked
export NOSTOS_BIN="$PWD/../nostosdb-cli/target/debug/nostos"
python3 <skill-root>/scripts/nostos_core.py resolve \
  --project <installed-provider-project> --json
```

When initializing through the `nostos` Skill, pass `--core-provider installed --core-binary "$NOSTOS_BIN"`; the latter records the reviewed path but does not replace the environment authorization.

## Required implementation tests

- native resolution priority and exact-version rejection;
- project-controlled `skills.core_binary` non-execution plus explicit user override;
- no fallback after an explicit or discovered version mismatch;
- installed-only mode never invokes npx;
- auto fallback only when no native candidate exists;
- exact package/version vector without shell interpolation;
- argument, stdout, stderr, and exit-code equivalence across providers;
- missing npx, offline/cache failure, unsupported platform, and interrupted child behavior;
- the existing Codex/Claude portable fixture producing identical canonical source hashes, logical database checksums, counts, warnings, and unresolved rows through both providers.

Use `nostos_core.py resolve --json` to inspect the selected provider and its exact argument vector. Native default output remains the binary path for compatibility; an npx provider has no persistent binary path.
