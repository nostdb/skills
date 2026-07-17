# Claude adapter

This adapter selects the Claude project discovery directory and delegates installation to the shared installer. It does not fork canonical Skill content.

```bash
python3 adapters/claude/install.py --project /path/to/project
```

The default copy mode installs identical Skills under `.claude/skills` and shared support under `.claude/references` and `.claude/scripts`. Existing paths are refused unless `--force` is explicit. `--mode symlink` is available for local development.
