#!/usr/bin/env python3
"""Expose deterministic help, initialization, and removal for the nostdb Skill."""

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
  help    Show this action summary without inspecting or changing a source root.
  init    Initialize one guarded centralized Source Mode project.
  remove  Delete NostDB configuration, sources, databases, and sidecars below
          one explicitly selected source root.

Init defaults:
  --core-version 0.0.1
  --core-provider auto
  --database graph.nostdb

Use --allow-nonempty only after confirming the destination is the intended
existing project. Initialization never replaces nostdb.json or the selected
source entry. Removal refuses broad roots, symlink boundaries, and an open
database; use --dry-run to inspect its complete target list without deleting.
"""


def main(arguments: Optional[List[str]] = None) -> int:
    """Dispatch one public Skill action without a shell."""

    values = list(sys.argv[1:] if arguments is None else arguments)
    if not values or values[0] in {"help", "-h", "--help"}:
        print(HELP, end="")
        return 0
    if values[0] in {"init", "remove"}:
        helper = Path(__file__).resolve().with_name("nostdb_project.py")
        try:
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
