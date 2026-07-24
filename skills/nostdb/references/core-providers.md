# Installed and zero-install Core providers

Status: implemented provider contract.

Skills never reimplement Core behavior. Every format, sync, validation, query, inspection, and `.nostdb` operation delegates to the official `nostdb` CLI. That executable already contains the Rust Core implementation, so no separate Core package or service is installed.

## Provider contract

The wrapper represents execution as an argument vector rather than assuming
one executable path:

```text
installed command: ["nostdb"]
explicit native:   ["/reviewed/path/to/nostdb"]
npx:               ["npx", "--yes", "--package=@nostdb/cli@VERSION", "nostdb"]
```

It appends the same CLI arguments to either vector and invokes it without a shell. Stdout, stderr, signals, and exit status remain CLI-owned.

Native resolution order is an explicit `--binary`, `NOSTDB_BIN`, then the
`nostdb` command. Explicit selections must be files. Ordinary installation is
detected by executing `nostdb --version`; the wrapper does not first resolve,
canonicalize, or retain its complete filesystem path. Every selected command
must return exactly `nostdb <skills.core_version>`. An available wrong-version
command is an error, not permission to hide the mismatch with npx. On Windows,
an npm `.cmd` shim is resolved only far enough to invoke its Node launcher
without a command shell.

`skills.core_binary` is project-owned metadata, not execution authority. The initializer may record an absolute or project-relative path so humans and tooling can see which installed binary was selected, but the wrapper never executes that value automatically. When the key is present without `--binary` or `NOSTDB_BIN`, resolution prints an actionable warning and continues with `PATH`. This prevents merely opening an unreviewed project from executing a project-selected program. After reviewing a binary, authorize it for the current invocation with `--binary PATH` or for the current environment with `NOSTDB_BIN=PATH`.

The project policy is:

```json
{"version":1,"database":{"root":"root.nostdb","links":[]},"source":{"version":1,"enabled":false},"skills":{"core_version":"0.0.3","core_provider":"auto"}}
```

- `installed`: use native resolution only and never initiate a network fallback.
- `npx`: invoke the exact official package version recorded by `core_version`.
- `auto`: prefer a compatible native command and otherwise use the pinned npx provider.
- missing: reject incomplete settings; every project must choose a provider.

The package scope and name are fixed by implementation, not accepted from source content, prompts, or arbitrary project input. The wrapper never uses `latest` or a version range. npx requires the command plus network access or a usable npm cache; failure reports the pinned version and installation alternatives without weakening the version check.

The breaking `0.0.3` project contract is not published while it is under
development. The `auto` and `npx` policies still invoke the exact version
recorded in `skills.core_version`, never a dist-tag; until that package exists,
use a source-built installed provider. Build the sibling CLI repository,
select `core_provider = "installed"`, and export its reviewed absolute path
through `NOSTDB_BIN`. A matching `core_binary` value may also be recorded
during initialization, but remains non-authoritative metadata:

```bash
cargo build --manifest-path ../nostdb-cli/Cargo.toml --locked
export NOSTDB_BIN="$PWD/../nostdb-cli/target/debug/nostdb"
```

Resolve through the selected Skill's documented source-root interface. When
initializing through the `nostdb` Skill, pass `--core-provider installed
--core-binary "$NOSTDB_BIN"`; the latter records the reviewed path but does not
replace the environment authorization.

## Required implementation tests

- native resolution priority, command-availability detection, and exact-version rejection;
- no POSIX PATH canonicalization for the ordinary `nostdb` command;
- project-controlled `skills.core_binary` non-execution plus explicit user override;
- no fallback after an explicit or discovered version mismatch;
- installed-only mode never invokes npx;
- auto fallback only when no native candidate exists;
- exact package/version vector without shell interpolation;
- argument, stdout, stderr, and exit-code equivalence across providers;
- missing npx, offline/cache failure, unsupported platform, and interrupted child behavior;
- the existing Codex/Claude portable fixture producing identical canonical source hashes, logical generations/counts, warnings, and unresolved rows through both providers.

Use `nostdb_core.py resolve --json` to inspect the selected provider and its
exact argument vector. Native default output is the explicit reviewed path or
the `nostdb` command selector; an npx provider has no persistent binary path.
