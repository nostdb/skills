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

Native resolution order is an explicit `--binary`, `NOSTOS_BIN`, project-relative or absolute `skills.core_binary`, then `nostos` on `PATH`. Each candidate must be a file and must return exactly `nostos <skills.core_version>` from `--version`. An existing wrong-version candidate is an error, not permission to hide the mismatch with npx.

The project policy is:

```toml
[skills]
core_version = "0.1.0"
database = "graph.ndb"
core_provider = "auto" # auto | installed | npx
```

- `installed`: use native resolution only and never initiate a network fallback.
- `npx`: invoke the exact official package version recorded by `core_version`.
- `auto`: prefer a compatible native binary and otherwise use the pinned npx provider.
- missing: preserve current installed-only behavior for existing projects until explicit configuration or migration.

The package scope and name are fixed by implementation, not accepted from source content, prompts, or arbitrary project input. The wrapper never uses `latest` or a version range. npx requires the command plus network access or a usable npm cache; failure reports the pinned version and installation alternatives without weakening the version check.

## Required implementation tests

- native resolution priority and exact-version rejection;
- no fallback after an explicit or discovered version mismatch;
- installed-only mode never invokes npx;
- auto fallback only when no native candidate exists;
- exact package/version vector without shell interpolation;
- argument, stdout, stderr, and exit-code equivalence across providers;
- missing npx, offline/cache failure, unsupported platform, and interrupted child behavior;
- the existing Codex/Claude portable fixture producing identical canonical source hashes, logical database checksums, counts, warnings, and unresolved rows through both providers.

Use `nostos_core.py resolve --json` to inspect the selected provider and its exact argument vector. Native default output remains the binary path for compatibility; an npx provider has no persistent binary path.
