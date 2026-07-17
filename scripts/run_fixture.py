#!/usr/bin/env python3
"""Exercise one shared fixture through an installed adapter and the public CLI."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from install_adapter import install


class FixtureError(RuntimeError):
    """A fixture setup or Core invocation failure."""


def run(command, capture=True):
    completed = subprocess.run(
        [str(value) for value in command],
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,
        text=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
        raise FixtureError("command failed ({}): {}".format(completed.returncode, stderr))
    return completed.stdout or b""


def execute(adapter_directory: str, args: argparse.Namespace) -> dict:
    fixture = args.fixture.resolve()
    output = args.output.resolve()
    manifest = json.loads((fixture / "fixture.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=False)
    install(output, adapter_directory, "copy", False)
    scripts = output / adapter_directory / "scripts"
    run(
        [
            sys.executable,
            scripts / "nostos_project.py",
            "init",
            "--project",
            output,
            "--layout",
            manifest["layout"],
            "--core-version",
            manifest["core_version"],
            "--core-binary",
            str(args.binary.resolve()),
            "--module-id",
            manifest["module_id"],
            "--allow-nonempty",
        ]
    )
    source = output / manifest["source_path"]
    shutil.copyfile(str(fixture / "source.nostos"), str(source))
    formatted = run(
        [
            sys.executable,
            scripts / "nostos_core.py",
            "run",
            "--project",
            output,
            "--",
            "format",
            "--file",
            source,
            "--project",
            output,
        ]
    )
    source.write_bytes(formatted)
    database = output / "graph.ndb"
    run(
        [
            sys.executable,
            scripts / "nostos_core.py",
            "run",
            "--project",
            output,
            "--",
            "sync",
            "--project",
            output,
            "--database",
            database,
            "--format",
            "json",
        ]
    )
    inspection = json.loads(
        run(
            [
                sys.executable,
                scripts / "nostos_core.py",
                "run",
                "--project",
                output,
                "--",
                "inspect",
                "--database",
                database,
                "--format",
                "json",
            ]
        ).decode("utf-8")
    )
    statistics = json.loads(
        run(
            [
                sys.executable,
                scripts / "nostos_core.py",
                "run",
                "--project",
                output,
                "--",
                "stats",
                "--database",
                database,
                "--format",
                "json",
            ]
        ).decode("utf-8")
    )
    run(
        [
            sys.executable,
            scripts / "nostos_core.py",
            "run",
            "--project",
            output,
            "--",
            "check",
            "--database",
            database,
            "--format",
            "json",
        ]
    )
    return {
        "inspection": inspection,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "statistics": statistics,
    }


def main(adapter_directory: str) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(execute(adapter_directory, args), sort_keys=True, separators=(",", ":")))
        return 0
    except (FixtureError, OSError, ValueError, KeyError) as error:
        print("nostos-fixture: {}".format(error), file=sys.stderr)
        return 1
