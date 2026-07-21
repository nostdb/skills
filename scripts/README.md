# Deterministic helpers

- `nostos_project.py`: initialize a layout and persist layout/Core selection in `nostos.toml`
- `nostos_skill.py`: expose deterministic `help` and guarded `init` actions for the public `nostos` Skill
- `nostos_core.py`: resolve an exactly pinned native or npx CLI provider and invoke it without a shell
- `nostos_provenance.py`: hash one document/code input and emit a portable provenance comment
- `nostos_source.py`: hash-guard installation of one complete canonical `.nostos` file
- `install_adapter.py`: copy or link the self-contained canonical Skill directories into one legacy adapter root
- `run_fixture.py`: exercise a shared fixture through an installed adapter and public CLI

These helpers may create configuration and `.nostos` source. They never implement parsing or storage and never write `.ndb`; only `nostos sync` receives a database path.

The standalone Skill directories bundle the helpers they need. Repository verification checks those runtime copies against these canonical development sources. The native-first, pinned-`npx` provider behavior is specified in [`core-providers.md`](../references/core-providers.md).
