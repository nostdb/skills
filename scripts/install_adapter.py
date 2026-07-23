#!/usr/bin/env python3
"""Install self-contained canonical Skills into one agent configuration root."""

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List


SKILL_NAMES = (
    "nostdb",
    "nostdb-visualize",
)


class InstallError(RuntimeError):
    """A safe adapter-installation failure."""


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def install(project: Path, adapter_directory: str, mode: str, force: bool) -> dict:
    project = project.resolve()
    if mode not in {"copy", "symlink"}:
        raise InstallError("adapter mode must be copy or symlink")
    if Path(adapter_directory).name != adapter_directory or not adapter_directory.startswith("."):
        raise InstallError("adapter directory must be one hidden path component")
    root = project / adapter_directory
    skills_root = root / "skills"
    for boundary in (root, skills_root):
        if boundary.is_symlink():
            raise InstallError(
                "refusing adapter path with symlink boundary: {}".format(boundary)
            )
    skills_root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink() or skills_root.is_symlink():
        raise InstallError("adapter path changed to a symlink during installation")
    destinations = [
        (repository_root() / "skills" / name, skills_root / name, True)
        for name in SKILL_NAMES
    ]
    existing = [
        destination
        for _, destination, _ in destinations
        if destination.exists() or destination.is_symlink()
    ]
    if existing and not force:
        raise InstallError("refusing to replace existing adapter path: {}".format(existing[0]))
    transaction = Path(
        tempfile.mkdtemp(prefix=".nost-install-", dir=str(skills_root))
    )
    staged = transaction / "staged"
    backups = transaction / "backups"
    staged.mkdir()
    backups.mkdir()
    installed: List[Path] = []
    backed_up: List[tuple] = []
    try:
        for source, destination, is_directory in destinations:
            staged_destination = staged / destination.name
            if mode == "copy":
                if is_directory:
                    shutil.copytree(
                        str(source),
                        str(staged_destination),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                    )
                else:
                    shutil.copy2(str(source), str(staged_destination))
            else:
                os.symlink(
                    str(source), str(staged_destination), target_is_directory=is_directory
                )
        for _, destination, _ in destinations:
            if destination.exists() or destination.is_symlink():
                backup = backups / destination.name
                os.replace(str(destination), str(backup))
                backed_up.append((backup, destination))
        for _, destination, _ in destinations:
            os.replace(str(staged / destination.name), str(destination))
            installed.append(destination)
    except BaseException:
        for destination in reversed(installed):
            if destination.is_symlink():
                destination.unlink()
            elif destination.is_dir():
                shutil.rmtree(str(destination))
            elif destination.exists():
                destination.unlink()
        for backup, destination in reversed(backed_up):
            if backup.exists() or backup.is_symlink():
                os.replace(str(backup), str(destination))
        raise
    finally:
        shutil.rmtree(str(transaction), ignore_errors=True)
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
        print("nostdb-skill-installer: {}".format(error), file=sys.stderr)
        return 2
