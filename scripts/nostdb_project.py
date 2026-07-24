#!/usr/bin/env python3
"""Configure, discover, or remove a portable NostDB project."""

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
    configured_database,
    project_document,
    read_text,
    validate_core_provider,
    validate_core_version,
    validate_root_path,
)


DEFAULT_CORE_VERSION = "0.0.3"
PROJECT_DIRECTORY = ".nostdb"
IGNORED_DISCOVERY_DIRECTORIES = frozenset(
    {".git", ".hg", ".svn", "node_modules", "target"}
)


def _settings_text(document: dict) -> str:
    return (
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )


def configure(args: argparse.Namespace) -> dict:
    project = args.src.expanduser().resolve()
    original = read_text(project)
    document = project_document(project)
    updated = {}
    skills = document.setdefault("skills", {})
    if not isinstance(skills, dict):
        raise ConfigError("settings.json skills must be an object")
    if args.core_version:
        skills["core_version"] = validate_core_version(args.core_version)
        updated["core_version"] = args.core_version
    if args.core_binary:
        skills["core_binary"] = args.core_binary
        updated["core_binary"] = args.core_binary
    if args.core_provider:
        skills["core_provider"] = validate_core_provider(args.core_provider)
        updated["core_provider"] = args.core_provider
    source = document.get("source")
    if not isinstance(source, dict):
        raise ConfigError("settings.json source must be an object")
    if args.source_enabled is not None:
        source["enabled"] = args.source_enabled == "true"
        updated["source_enabled"] = source["enabled"]
    database = document.get("database")
    if not isinstance(database, dict):
        raise ConfigError("settings.json database must be an object")
    if args.root:
        root = validate_root_path(args.root)
        current = configured_database(project)
        if root != current and (project / PROJECT_DIRECTORY / current).exists():
            raise ConfigError(
                "cannot rename an existing database through settings; use the native CLI"
            )
        database["root"] = root
        updated["root"] = root
    if not updated:
        raise ConfigError("configure requires at least one value")
    atomic_write(config_path(project), _settings_text(document), expected_text=original)
    return {"settings": str(config_path(project)), "updated": updated}


def _direct_child_projects(project: Path) -> List[Path]:
    children = []
    for directory, names, _files in os.walk(
        str(project), topdown=True, followlinks=False
    ):
        current = Path(directory)
        retained = []
        for name in sorted(names):
            candidate = current / name
            if candidate.is_symlink() or name in IGNORED_DISCOVERY_DIRECTORIES:
                continue
            if name == PROJECT_DIRECTORY:
                continue
            retained.append(name)
        names[:] = retained
        if current == project:
            continue
        storage = current / PROJECT_DIRECTORY
        settings = storage / "settings.json"
        if storage.is_symlink() or settings.is_symlink():
            continue
        if storage.is_dir() and settings.is_file():
            children.append(current)
            names[:] = []
    return sorted(children, key=lambda path: path.relative_to(project).as_posix())


def refresh_links(project: Path) -> List[dict]:
    requested = project.expanduser().absolute()
    if requested.is_symlink():
        raise ConfigError("project root must not be a symlink: {}".format(requested))
    project = requested.resolve()
    storage = project / PROJECT_DIRECTORY
    settings = storage / "settings.json"
    if storage.is_symlink() or settings.is_symlink():
        raise ConfigError("project settings must not cross a symlink: {}".format(settings))
    original = read_text(project)
    document = project_document(project)
    database = document.get("database")
    if not isinstance(database, dict):
        raise ConfigError("settings.json database must be an object")
    own_root = configured_database(project)
    own_database = project / PROJECT_DIRECTORY / own_root
    if not own_database.is_file():
        raise ConfigError("configured database does not exist: {}".format(own_database))

    links = []
    for child in _direct_child_projects(project):
        refresh_links(child)
        root = configured_database(child)
        child_database = child / PROJECT_DIRECTORY / root
        if not child_database.is_file():
            raise ConfigError(
                "linked project database does not exist: {}".format(child_database)
            )
        links.append(
            {
                "project": child.relative_to(project).as_posix(),
                "root": root,
            }
        )
    links.sort(key=lambda link: link["project"])
    if database.get("links") != links:
        database["links"] = links
        atomic_write(
            config_path(project),
            _settings_text(document),
            expected_text=original,
        )
    return links


def refresh(args: argparse.Namespace) -> dict:
    project = args.src.expanduser().resolve()
    links = refresh_links(project)
    return {
        "links": links,
        "root": configured_database(project),
        "settings": str(config_path(project)),
        "src": str(project),
    }


def _removal_targets(src: Path) -> List[Path]:
    targets = []
    for directory, names, _files in os.walk(
        str(src), topdown=True, followlinks=False
    ):
        current = Path(directory)
        retained = []
        for name in names:
            candidate = current / name
            if candidate.is_symlink():
                continue
            if name == PROJECT_DIRECTORY:
                targets.append(candidate)
                continue
            retained.append(name)
        names[:] = retained
    return sorted(targets, key=lambda path: path.relative_to(src).as_posix())


def _assert_no_symlink_boundary(targets: List[Path]) -> None:
    for target in targets:
        if target.is_symlink():
            raise ConfigError("refusing to remove symlinked NostDB path: {}".format(target))
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
        for lock in target.rglob("*.nostdb.lock"):
            if lock.is_file():
                _assert_database_lock_available(lock)
    relative = [target.relative_to(src).as_posix() for target in targets]
    if args.dry_run:
        return {"dry_run": True, "removed": [], "src": str(src), "targets": relative}
    for target in sorted(targets, key=lambda path: len(path.parts), reverse=True):
        shutil.rmtree(str(target))
    return {"dry_run": False, "removed": relative, "src": str(src)}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    change = commands.add_parser("configure", help="persist project settings")
    change.add_argument("--src", type=Path, required=True)
    change.add_argument("--core-version")
    change.add_argument("--core-provider", choices=CORE_PROVIDERS)
    change.add_argument("--core-binary")
    change.add_argument("--source-enabled", choices=("true", "false"))
    change.add_argument("--root")
    change.set_defaults(handler=configure)
    discover = commands.add_parser(
        "refresh", help="discover and record nested project links"
    )
    discover.add_argument("--src", type=Path, required=True)
    discover.set_defaults(handler=refresh)
    remove_command = commands.add_parser(
        "remove", help="delete project-local NostDB directories below one root"
    )
    remove_command.add_argument("--src", type=Path, required=True)
    remove_command.add_argument("--dry-run", action="store_true")
    remove_command.set_defaults(handler=remove)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        print(
            json.dumps(
                args.handler(args),
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except (ConfigError, OSError) as error:
        print("nostdb-project: {}".format(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
