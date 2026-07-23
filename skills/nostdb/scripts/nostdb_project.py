#!/usr/bin/env python3
"""Initialize, configure, or remove a portable NostDB project."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import List

from nostdb_config import (
    CORE_PROVIDERS,
    ConfigError,
    atomic_write,
    config_path,
    read_text,
    update_sections,
    update_values,
    validate_core_version,
    validate_core_provider,
    validate_root_path,
)


DEFAULT_CORE_VERSION = "0.0.1"
NDB_SUFFIXES = (
    ".nostdb",
    ".nostdb-wal",
    ".nostdb-shm",
    ".nostdb-journal",
    ".nostdb.lock",
    ".nostdb-lock",
)
TEMPORARY_PREFIXES = (".nost-config-", ".nost-source-", ".nost-restore-")


def initialize(args: argparse.Namespace) -> dict:
    project = args.src.resolve()
    configuration = config_path(project)
    if configuration.exists():
        raise ConfigError("refusing to replace existing {}".format(configuration))
    if project.exists() and any(project.iterdir()) and not args.allow_nonempty:
        raise ConfigError(
            "refusing to initialize a nonempty directory without --allow-nonempty: {}".format(
                project
            )
        )
    validate_core_version(args.core_version)
    validate_core_provider(args.core_provider)
    database_root = validate_root_path(".nostdb")
    database = project / database_root
    if database.exists():
        raise ConfigError("refusing to adopt existing {}".format(database))
    project.mkdir(parents=True, exist_ok=True)
    skills = {
        "core_version": args.core_version,
        "core_provider": args.core_provider,
    }
    if args.core_binary:
        skills["core_binary"] = args.core_binary
    text = json.dumps(
        {
            "nostdb": 1,
            "root": database_root,
            "nost": False,
            "skills": skills,
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"
    atomic_write(configuration, text)
    return {
        "config": str(configuration),
        "core_version": args.core_version,
        "root": database_root,
        "nost": False,
        "src": str(project),
    }


def configure(args: argparse.Namespace) -> dict:
    project = args.src.resolve()
    updates = {}
    skills = {}
    if args.core_version:
        skills["core_version"] = validate_core_version(args.core_version)
    if args.core_binary:
        skills["core_binary"] = args.core_binary
    if args.core_provider:
        skills["core_provider"] = validate_core_provider(args.core_provider)
    if args.nost is not None:
        updates["nost"] = args.nost == "true"
    if skills:
        updates["skills"] = skills
    if not updates:
        raise ConfigError("configure requires at least one value")
    text = read_text(project)
    skill_updates = updates.pop("skills", None)
    if skill_updates:
        text = update_sections(text, {"skills": skill_updates})
    updated_values = dict(updates)
    updated = update_values(text, updated_values) if updated_values else text
    atomic_write(config_path(project), updated)
    if skill_updates:
        updated_values["skills"] = skill_updates
    return {"config": str(config_path(project)), "updated": updated_values}


def _is_nostdb_artifact(name: str) -> bool:
    return (
        name == "nostdb.json"
        or name.endswith(".nost-lock")
        or name.endswith(NDB_SUFFIXES)
        or name.startswith(TEMPORARY_PREFIXES)
    )


def _removal_targets(src: Path) -> List[Path]:
    targets = set()
    for directory, names, files in os.walk(str(src), topdown=True, followlinks=False):
        parent = Path(directory)
        for name in list(names):
            candidate = parent / name
            if name == ".nost":
                targets.add(candidate)
                names.remove(name)
            elif candidate.is_symlink():
                names.remove(name)
        for name in files:
            if _is_nostdb_artifact(name):
                targets.add(parent / name)
    return sorted(targets, key=lambda path: path.relative_to(src).as_posix())


def _assert_no_symlink_boundary(targets: List[Path]) -> None:
    for target in targets:
        if target.is_symlink():
            raise ConfigError("refusing to remove symlinked NostDB path: {}".format(target))
        if target.is_dir():
            for nested in target.rglob("*"):
                if nested.is_symlink():
                    raise ConfigError(
                        "refusing to remove through symlink boundary: {}".format(nested)
                    )


def _assert_database_lock_available(path: Path) -> None:
    acquired = False
    try:
        with path.open("a+b") as lock:
            if os.name == "nt":
                import msvcrt

                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                acquired = True
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    except OSError as error:
        raise ConfigError(
            "refusing to remove an open NostDB database; stop its owner first: {}".format(
                path
            )
        ) from error
    if not acquired:
        raise ConfigError("cannot verify database ownership lock: {}".format(path))


def remove(args: argparse.Namespace) -> dict:
    requested = args.src.expanduser().absolute()
    if requested.is_symlink():
        raise ConfigError("project root must not be a symlink: {}".format(requested))
    src = requested.resolve()
    if not src.is_dir():
        raise ConfigError("project root is not a directory: {}".format(src))
    if src.parent == src or src == Path.home().resolve():
        raise ConfigError("refusing broad project root removal: {}".format(src))
    configuration = config_path(src)
    if configuration.is_symlink() or not configuration.is_file():
        raise ConfigError("refusing removal without a regular {}".format(configuration))
    targets = _removal_targets(src)
    _assert_no_symlink_boundary(targets)
    for target in targets:
        if not target.is_file() and not target.is_dir():
            raise ConfigError("refusing non-regular NostDB path: {}".format(target))
        if target.name.endswith(".nostdb.lock") and target.is_file():
            _assert_database_lock_available(target)
    relative = [target.relative_to(src).as_posix() for target in targets]
    if args.dry_run:
        return {"dry_run": True, "removed": [], "src": str(src), "targets": relative}
    for target in sorted(
        (path for path in targets if path.is_file() and path != configuration),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        target.unlink()
    for target in sorted(
        (path for path in targets if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        shutil.rmtree(str(target))
    configuration.unlink()
    return {"dry_run": False, "removed": relative, "src": str(src)}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a new NDB-only project configuration")
    init.add_argument("--src", type=Path, required=True)
    init.add_argument("--core-version", default=DEFAULT_CORE_VERSION)
    init.add_argument("--core-provider", choices=CORE_PROVIDERS, default="auto")
    init.add_argument("--core-binary")
    init.add_argument("--allow-nonempty", action="store_true")
    init.set_defaults(handler=initialize)
    change = commands.add_parser("configure", help="persist Core selection")
    change.add_argument("--src", type=Path, required=True)
    change.add_argument("--core-version")
    change.add_argument("--core-provider", choices=CORE_PROVIDERS)
    change.add_argument("--core-binary")
    change.add_argument("--nost", choices=("true", "false"))
    change.set_defaults(handler=configure)
    remove_command = commands.add_parser(
        "remove", help="delete project-local NostDB files below one project root"
    )
    remove_command.add_argument("--src", type=Path, required=True)
    remove_command.add_argument("--dry-run", action="store_true")
    remove_command.set_defaults(handler=remove)
    return root


def main() -> int:
    try:
        result = parser().parse_args()
        print(json.dumps(result.handler(result), sort_keys=True, separators=(",", ":")))
        return 0
    except (ConfigError, OSError) as error:
        print("nostdb-project: {}".format(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
