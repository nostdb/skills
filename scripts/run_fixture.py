#!/usr/bin/env python3
"""Exercise one shared fixture through an installed Skill and the public CLI."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Union

from install_adapter import install


class FixtureError(RuntimeError):
    """A fixture setup or Core invocation failure."""


CommandPart = Union[str, Path]


def load_manifest(fixture: Path) -> dict:
    """Validate the complete fixture schema before creating output paths."""

    manifest_path = fixture / "fixture.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FixtureError("cannot read valid fixture manifest: {}".format(error)) from error
    required = {"core_version", "layout", "module_id", "source_path"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise FixtureError("fixture manifest must contain exactly {}".format(sorted(required)))
    if any(not isinstance(manifest[key], str) for key in required):
        raise FixtureError("fixture manifest values must be strings")
    if manifest["layout"] != "centralized":
        raise FixtureError("fixture manifest layout must be centralized")
    source_path = Path(manifest["source_path"])
    if (
        not manifest["source_path"]
        or "\\" in manifest["source_path"]
        or source_path.is_absolute()
        or ".." in source_path.parts
        or "." in source_path.parts
        or source_path.suffix != ".nost"
    ):
        raise FixtureError("fixture source_path must be a normalized relative .nost path")
    source = fixture / "source.nost"
    if source.is_symlink() or not source.is_file():
        raise FixtureError("fixture must contain one regular non-symlink source.nost")
    return manifest


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


def core_command(
    scripts: Path,
    project: Path,
    binary: Optional[Path],
    arguments: Sequence[CommandPart],
) -> List[CommandPart]:
    """Build one wrapper command while preserving explicit binary authority."""

    command: List[CommandPart] = [
        sys.executable,
        scripts / "nostdb_core.py",
        "run",
        "--src",
        project,
    ]
    if binary:
        command.extend(["--binary", binary.resolve()])
    command.extend(["--"] + list(arguments))
    return command


def execute(adapter_directory: str, args: argparse.Namespace) -> dict:
    fixture = args.fixture.resolve()
    output = args.output.resolve()
    manifest = load_manifest(fixture)
    output.mkdir(parents=True, exist_ok=False)
    try:
        return execute_created(adapter_directory, args, fixture, output, manifest)
    except BaseException:
        shutil.rmtree(str(output), ignore_errors=True)
        raise


def execute_created(
    adapter_directory: str,
    args: argparse.Namespace,
    fixture: Path,
    output: Path,
    manifest: dict,
) -> dict:
    """Run a validated fixture inside a newly created disposable output."""

    install(output, adapter_directory, "copy", False)
    scripts = output / adapter_directory / "skills" / "nostdb" / "scripts"
    initialize = [
        sys.executable,
        scripts / "nostdb_project.py",
        "init",
        "--src",
        output,
        "--core-version",
        manifest["core_version"],
        "--core-provider",
        args.core_provider,
        "--module-id",
        manifest["module_id"],
        "--allow-nonempty",
    ]
    if args.binary:
        initialize.extend(["--core-binary", str(args.binary.resolve())])
    run(initialize)
    source = output / manifest["source_path"]
    shutil.copyfile(str(fixture / "source.nost"), str(source))
    formatted = run(
        core_command(
            scripts,
            output,
            args.binary,
            [
                "format",
                "--file",
                source,
                "--project",
                output,
            ],
        )
    )
    source.write_bytes(formatted)
    database = output / "graph.nostdb"
    run(
        core_command(
            scripts,
            output,
            args.binary,
            [
                "sync",
                "--project",
                output,
                "--database",
                database,
                "--format",
                "json",
            ],
        )
    )
    inspection = json.loads(
        run(
            core_command(
                scripts,
                output,
                args.binary,
                [
                    "inspect",
                    "--database",
                    database,
                    "--format",
                    "json",
                ],
            )
        ).decode("utf-8")
    )
    statistics = json.loads(
        run(
            core_command(
                scripts,
                output,
                args.binary,
                [
                    "stats",
                    "--database",
                    database,
                    "--format",
                    "json",
                ],
            )
        ).decode("utf-8")
    )
    warnings = json.loads(
        run(
            core_command(
                scripts,
                output,
                args.binary,
                [
                    "warnings",
                    "--project",
                    output,
                    "--format",
                    "json",
                ],
            )
        ).decode("utf-8")
    )
    unresolved = json.loads(
        run(
            core_command(
                scripts,
                output,
                args.binary,
                [
                    "unresolved",
                    "--database",
                    database,
                    "--format",
                    "json",
                ],
            )
        ).decode("utf-8")
    )
    run(
        core_command(
            scripts,
            output,
            args.binary,
            [
                "check",
                "--database",
                database,
                "--format",
                "json",
            ],
        )
    )
    visualize = [
        sys.executable,
        output
        / adapter_directory
        / "skills"
        / "nostdb-visualize"
        / "scripts"
        / "nostdb_core.py",
        "run",
    ]
    if args.binary:
        visualize.extend(["--binary", args.binary.resolve()])
    else:
        visualize.extend(["--project", output])
    visualize.extend(["--database", database, "--"])
    run(
        visualize
        + [
            "query",
            "--read-only",
            "MATCH (n) RETURN n ORDER BY id(n) LIMIT 1",
            "--format",
            "json",
        ]
    )
    rejected_write = subprocess.run(
        [str(value) for value in visualize + ["query", "--read-only", "CREATE (n)"]],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    if rejected_write.returncode != 4 or b"read-only" not in rejected_write.stderr:
        raise FixtureError(
            "visualization wrapper did not reject a write with query exit 4"
        )
    after_rejection = json.loads(
        run(visualize + ["stats", "--format", "json"]).decode("utf-8")
    )
    if after_rejection != statistics:
        raise FixtureError("visualization write rejection changed database statistics")
    return {
        "inspection": inspection,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "statistics": statistics,
        "unresolved": unresolved,
        "warnings": warnings,
    }


def main(adapter_directory: str) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--binary", type=Path)
    parser.add_argument(
        "--core-provider", choices=("auto", "installed", "npx"), default="installed"
    )
    args = parser.parse_args()
    try:
        if args.core_provider == "installed" and args.binary is None:
            raise FixtureError("installed fixture provider requires --binary")
        print(json.dumps(execute(adapter_directory, args), sort_keys=True, separators=(",", ":")))
        return 0
    except (FixtureError, OSError, ValueError, KeyError) as error:
        print("nostdb-fixture: {}".format(error), file=sys.stderr)
        return 1
