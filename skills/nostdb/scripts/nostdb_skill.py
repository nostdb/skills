#!/usr/bin/env python3
"""Expose deterministic help, initialization, and removal for the nostdb Skill."""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


HELP = """NostDB Skill

Usage:
  nostdb help
  nostdb init --src PATH [options]
  nostdb remove --src PATH [--dry-run]
  nostdb <natural-language task>

Actions:
  help    Show this action summary without inspecting or changing a project.
  init    Initialize one guarded NDB-only project and create its database.
  remove  Delete NostDB configuration, sources, databases, and sidecars below
          one explicitly selected project root.

Init defaults:
  --core-version 0.0.1
  --core-provider auto

Use --allow-nonempty only after confirming the destination is the intended
existing project. Initialization never replaces nostdb.json or the selected
`.nostdb`. Removal refuses broad roots, symlink boundaries, and an open database;
use --dry-run to inspect its complete target list without deleting.
"""


def _run_init(helper: Path, values: List[str]) -> int:
    completed = subprocess.run(
        [sys.executable, str(helper), "init"] + values,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        return completed.returncode
    try:
        payload = json.loads(completed.stdout)
        project = Path(payload["src"])
        database = project / payload["root"]
    except (KeyError, TypeError, ValueError) as error:
        print(
            "nostdb-skill: invalid project helper response: {}".format(error),
            file=sys.stderr,
        )
        return 3
    core = Path(__file__).resolve().with_name("nostdb_core.py")
    core_arguments = [sys.executable, str(core), "run", "--src", str(project)]
    if "--core-binary" in values:
        index = values.index("--core-binary")
        if index + 1 < len(values):
            core_arguments.extend(["--binary", values[index + 1]])
    core_arguments.extend(
        [
            "--",
            "sync",
            "--project",
            str(project),
            "--format",
            "json",
        ]
    )
    synchronized = subprocess.run(
        core_arguments,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if synchronized.returncode != 0 or not database.is_file():
        try:
            (project / "nostdb.json").unlink()
        except FileNotFoundError:
            pass
        for suffix in ("", ".lock", "-wal", "-shm", "-journal"):
            try:
                Path(str(database) + suffix).unlink()
            except FileNotFoundError:
                pass
        sys.stderr.write(synchronized.stderr)
        if synchronized.returncode == 0:
            print(
                "nostdb-skill: Core did not create {}".format(database),
                file=sys.stderr,
            )
            return 3
        return synchronized.returncode
    sys.stderr.write(synchronized.stderr)
    print(completed.stdout, end="")
    return 0


def main(arguments: Optional[List[str]] = None) -> int:
    """Dispatch one public Skill action without a shell."""

    values = list(sys.argv[1:] if arguments is None else arguments)
    if not values or values[0] in {"help", "-h", "--help"}:
        print(HELP, end="")
        return 0
    if values[0] in {"init", "remove"}:
        helper = Path(__file__).resolve().with_name("nostdb_project.py")
        try:
            if values[0] == "init":
                return _run_init(helper, values[1:])
            completed = subprocess.run(
                [sys.executable, str(helper), values[0]] + values[1:],
                check=False,
            )
        except OSError as error:
            print(
                "nostdb-skill: cannot run project helper: {}".format(error),
                file=sys.stderr,
            )
            return 3
        return completed.returncode
    print(
        "nostdb-skill: unknown action {!r}; use 'help', 'init', 'remove', or "
        "describe the NostDB task".format(values[0]),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
