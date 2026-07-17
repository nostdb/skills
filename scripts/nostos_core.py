#!/usr/bin/env python3
"""Locate an exactly pinned Nostos CLI and invoke it without a shell."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from nostos_config import ConfigError, require_core_version, skill_values


VERSION_OUTPUT = re.compile(r"^nostos ([0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?)$")


class CoreResolutionError(RuntimeError):
    """A missing or incompatible public CLI boundary."""


def resolve(project: Path, explicit: Optional[str] = None) -> Path:
    project = project.resolve()
    expected = require_core_version(project)
    configured = skill_values(project).get("core_binary")
    selected = explicit or os.environ.get("NOSTOS_BIN") or configured
    if selected:
        candidate = Path(selected)
        if not candidate.is_absolute():
            candidate = project / candidate
        candidate = candidate.resolve()
    else:
        located = shutil.which("nostos")
        if located is None:
            raise CoreResolutionError(
                "cannot locate nostos {}; set skills.core_binary, NOSTOS_BIN, or PATH".format(expected)
            )
        candidate = Path(located).resolve()
    if not candidate.is_file():
        raise CoreResolutionError("configured Core binary does not exist: {}".format(candidate))
    try:
        completed = subprocess.run(
            [str(candidate), "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except OSError as error:
        raise CoreResolutionError("cannot execute {}: {}".format(candidate, error)) from error
    output = completed.stdout.strip()
    match = VERSION_OUTPUT.fullmatch(output)
    if completed.returncode != 0 or match is None:
        detail = completed.stderr.strip() or output or "no version output"
        raise CoreResolutionError("invalid nostos --version response from {}: {}".format(candidate, detail))
    actual = match.group(1)
    if actual != expected:
        raise CoreResolutionError(
            "Core version mismatch: expected {} from nostos.toml, found {} at {}".format(
                expected, actual, candidate
            )
        )
    return candidate


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    locate = commands.add_parser("resolve", help="print the compatible CLI path")
    locate.add_argument("--project", type=Path, required=True)
    locate.add_argument("--binary")
    locate.add_argument("--json", action="store_true")
    run = commands.add_parser("run", help="run the compatible CLI")
    run.add_argument("--project", type=Path, required=True)
    run.add_argument("--binary")
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        binary = resolve(args.project, args.binary)
        if args.command == "resolve":
            if args.json:
                values = skill_values(args.project)
                print(
                    json.dumps(
                        {
                            "binary": str(binary),
                            "database": values.get("database"),
                            "version": require_core_version(args.project),
                        },
                        sort_keys=True,
                    )
                )
            else:
                print(binary)
            return 0
        arguments: List[str] = list(args.arguments)
        if arguments and arguments[0] == "--":
            arguments.pop(0)
        if not arguments:
            raise CoreResolutionError("run requires arguments after --")
        return subprocess.run([str(binary)] + arguments, check=False).returncode
    except (ConfigError, CoreResolutionError) as error:
        print("nostos-core: {}".format(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
