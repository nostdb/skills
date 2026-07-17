# Deterministic helpers

- `nostos_project.py`: initialize a layout and persist layout/Core selection in `nostos.toml`
- `nostos_core.py`: resolve an exactly pinned public CLI and invoke it without a shell
- `nostos_provenance.py`: hash one document/code input and emit a portable provenance comment
- `nostos_source.py`: hash-guard installation of one complete canonical `.nostos` file
- `install_adapter.py`: copy or link canonical Skills/support into one adapter root
- `run_fixture.py`: exercise a shared fixture through an installed adapter and public CLI

These helpers may create configuration and `.nostos` source. They never implement parsing or storage and never write `.ndb`; only `nostos sync` receives a database path.
