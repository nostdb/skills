# Claude adapter

This adapter selects the Claude project discovery directory and delegates installation to the shared installer. It does not fork canonical Skill content.

```bash
python3 adapters/claude/install.py --project /path/to/project
```

This adapter remains only for repository compatibility tests; public installation uses `npx skills add nostosdb/skills --skill NAME`. The default copy mode installs exactly the two self-contained Skill directories under `.claude/skills` and creates no sibling support directories. Existing Skill paths are refused unless `--force` is explicit. `--mode symlink` is available for local development.
