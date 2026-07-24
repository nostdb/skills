# Installed WebGPU visualization plugin

The default interactive visualization is the self-contained
`nostdb-visualize` plugin from `nostdb/plugins`. The npm command downloads the
manager only; the plugin itself must be installed before execution.

Prefer an installed `nostdb-plugins` command. When it is unavailable, use the
public manager delivery command shown below.

## Project scope

Inspect the project installation:

```bash
npx --yes @nostdb/plugins@latest installed --project <project> --json
```

After reviewing the exact source, resolved commit, content digest, manifest,
and the `database:read`, `filesystem:project`, `network`, and `subprocess`
permissions, install only with explicit approval:

```bash
npx --yes @nostdb/plugins@latest add \
  nostdb/plugins@nostdb-visualize --project <project> --yes
```

Open the visualization:

```bash
npx --yes @nostdb/plugins@latest run nostdb-visualize \
  --project <project> -- open
```

Use `serve` instead of `open` when the user wants the private loopback URL
without launching a browser.

## Global scope

Global installation is explicit and remains separate from the target project:

```bash
npx --yes @nostdb/plugins@latest installed --global --json
npx --yes @nostdb/plugins@latest add \
  nostdb/plugins@nostdb-visualize --global --yes
npx --yes @nostdb/plugins@latest run nostdb-visualize \
  --global --project <project> -- open
```

Project content lives below `.nostdb/plugin/`; global content lives below
`~/.nostdb/plugin/`. Never switch scopes silently.

## Bounds

The plugin defaults to 20,000 nodes and 80,000 relationships. Narrow requests
with:

```text
--max-nodes COUNT
--max-edges COUNT
```

The plugin reads `.nostdb/settings.json` only to resolve the configured
database filename, then obtains graph entities through shell-free
`nostdb query --read-only` calls. It serves static assets and graph JSON from a
random, loopback-only URL and exposes no mutation endpoint. It never opens or
decodes the `*.nostdb` file.
