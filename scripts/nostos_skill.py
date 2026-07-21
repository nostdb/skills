#!/usr/bin/env python3
"""Expose deterministic help and initialization actions for the nostos Skill."""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional


HELP = """NostosDB Skill

Usage:
  nostos help
  nostos init --project PATH --layout centralized|colocated|single [options]
  nostos <natural-language task>

Actions:
  help  Show this action summary without inspecting or changing a project.
  init  Initialize one guarded Source Mode project through nostos_project.py.

Init defaults:
  --core-version 0.1.0
  --core-provider auto
  --database graph.ndb

Use --allow-nonempty only after confirming the destination is the intended
existing project. Initialization never replaces nostos.toml or the selected
source entry.
"""


def main(arguments: Optional[List[str]] = None) -> int:
    """Dispatch one public Skill action without a shell."""

    values = list(sys.argv[1:] if arguments is None else arguments)
    if not values or values[0] in {"help", "-h", "--help"}:
        print(HELP, end="")
        return 0
    if values[0] == "init":
        helper = Path(__file__).resolve().with_name("nostos_project.py")
        try:
            completed = subprocess.run(
                [sys.executable, str(helper), "init"] + values[1:],
                check=False,
            )
        except OSError as error:
            print(
                "nostos-skill: cannot run initialization helper: {}".format(error),
                file=sys.stderr,
            )
            return 3
        return completed.returncode
    print(
        "nostos-skill: unknown action {!r}; use 'help' or describe the NostosDB task"
        .format(values[0]),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
