# Deterministic helpers

- `nostdb_project.py`: initialize the NDB-only project, persist Core
  selection, and remove project-local NostDB artifacts
- `nostdb_skill.py`: expose deterministic `help`, guarded `init`, and scoped
  `remove` actions for the public `nostdb` Skill
- `nostdb_core.py`: resolve an exactly pinned native or npx CLI provider and invoke it without a shell
- `nostdb_provenance.py`: hash one document/code input and emit a portable provenance comment
- `nostdb_source.py`: hash-guard installation of one complete canonical `.nost` file
- `install_adapter.py`: copy or link the self-contained canonical Skill directories into one legacy adapter root
- `run_fixture.py`: exercise a shared fixture through an installed adapter and public CLI

These helpers may create configuration and `.nost` source. They never implement parsing or storage and never write `.nostdb`; only `nostdb sync` receives a database path.

The standalone Skill directories bundle the helpers they need. Repository verification checks those runtime copies against these canonical development sources. The native-first, pinned-`npx` provider behavior is specified in [`core-providers.md`](../references/core-providers.md).
