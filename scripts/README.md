# Deterministic helpers

- `nostdb_project.py`: persist Core/source selection, discover nested projects,
  refresh root links, and remove project-local NostDB directories
- `nostdb_skill.py`: resolve the Agent provider, delegate `init` and `update`
  to the native CLI, and expose scoped `remove`; static Skill help requires no
  script
- `nostdb_core.py`: resolve an exactly pinned native or npx CLI provider and invoke it without a shell
- `nostdb_provenance.py`: hash one document/code input and emit a portable provenance comment
- `nostdb_source.py`: hash-guard installation of one complete canonical `.nost` file
- `install_adapter.py`: copy or link the self-contained canonical Skill directories into one legacy adapter root
- `run_fixture.py`: exercise a shared fixture through an installed adapter and public CLI

These helpers may update configuration and `.nost` source. They never implement
parsing or storage and never write `.nostdb`; native `nostdb init` or `sync`
owns every database write.

The standalone Skill directories bundle the helpers they need. Repository verification checks those runtime copies against these canonical development sources. The native-first, pinned-`npx` provider behavior is specified in [`core-providers.md`](../references/core-providers.md).
