# Codex adapter

This adapter selects the Codex project discovery directory and delegates installation to the shared installer. It does not fork canonical Skill content.

```bash
python3 adapters/codex/install.py --project /path/to/project
```

The default copy mode installs identical Skills under `.agents/skills` and shared support under `.agents/references` and `.agents/scripts`. Existing paths are refused unless `--force` is explicit. `--mode symlink` is available for local development.
