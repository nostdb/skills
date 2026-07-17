#!/usr/bin/env python3
"""Install canonical Skills and shared support into one agent configuration root."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import List


SKILL_NAMES = (
    "nostos-orchestrator",
    "nostos-core",
    "nostos-ingest",
    "nostos-schema",
    "nostos-explore",
    "nostos-visualize",
)


class InstallError(RuntimeError):
    """A safe adapter-installation failure."""


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def install(project: Path, adapter_directory: str, mode: str, force: bool) -> dict:
    project = project.resolve()
    if Path(adapter_directory).name != adapter_directory or not adapter_directory.startswith("."):
        raise InstallError("adapter directory must be one hidden path component")
    root = project / adapter_directory
    destinations = [
        (repository_root() / "skills" / name, root / "skills" / name, True)
        for name in SKILL_NAMES
    ]
    destinations.extend(
        (source, root / "references" / source.name, False)
        for source in sorted((repository_root() / "references").iterdir())
        if source.is_file()
    )
    destinations.extend(
        (source, root / "scripts" / source.name, False)
        for source in sorted((repository_root() / "scripts").iterdir())
        if source.is_file() and source.suffix in {".py", ".md"}
    )
    existing = [
        destination
        for _, destination, _ in destinations
        if destination.exists() or destination.is_symlink()
    ]
    if existing and not force:
        raise InstallError("refusing to replace existing adapter path: {}".format(existing[0]))
    for _, destination, is_directory in destinations:
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or not is_directory:
                destination.unlink()
            else:
                shutil.rmtree(str(destination))
    created: List[Path] = []
    try:
        for source, destination, is_directory in destinations:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if mode == "copy":
                if is_directory:
                    shutil.copytree(
                        str(source),
                        str(destination),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                    )
                else:
                    shutil.copy2(str(source), str(destination))
            else:
                os.symlink(str(source), str(destination), target_is_directory=is_directory)
            created.append(destination)
    except BaseException:
        for destination in reversed(created):
            if destination.is_symlink():
                destination.unlink()
            elif destination.is_dir():
                shutil.rmtree(str(destination))
            elif destination.exists():
                destination.unlink()
        raise
    return {
        "adapter_root": str(root),
        "mode": mode,
        "skills": list(SKILL_NAMES),
    }


def main(adapter_directory: str) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--mode", choices=("copy", "symlink"), default="copy")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        result = install(args.project, adapter_directory, args.mode, args.force)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (InstallError, OSError) as error:
        print("nostos-skill-installer: {}".format(error), file=sys.stderr)
        return 2
