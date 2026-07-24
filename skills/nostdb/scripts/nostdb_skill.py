#!/usr/bin/env python3
"""Bridge guarded Skill init, update, and remove actions to NostDB Core."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from nostdb_config import (
    CORE_PROVIDERS,
    ConfigConflictError,
    ConfigError,
    atomic_write,
    config_path,
    configured_database,
    read_text,
    update_sections,
    validate_core_provider,
    validate_core_version,
    validate_root_path,
)
from nostdb_project import (
    DEFAULT_CORE_VERSION,
    refresh_links,
    remove,
)
from nostdb_provider import (
    CoreResolutionError,
    resolve_provider,
    resolve_requested_provider,
)


def _cleanup_init(project: Path, root: str) -> None:
    storage = project / ".nostdb"
    configuration = config_path(project)
    database = storage / root
    try:
        configuration.unlink()
    except FileNotFoundError:
        pass
    for suffix in ("", ".lock", "-wal", "-shm", "-journal"):
        try:
            Path(str(database) + suffix).unlink()
        except FileNotFoundError:
            pass
    try:
        storage.rmdir()
    except OSError:
        pass


def _run(command: list) -> object:
    import subprocess

    try:
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CoreResolutionError(
            "cannot execute Core provider {}: {}".format(command[0], error)
        ) from error


def initialize(args: argparse.Namespace) -> int:
    project = args.src.expanduser().resolve()
    version = validate_core_version(args.core_version)
    policy = validate_core_provider(args.core_provider)
    root = validate_root_path(args.root)
    provider = resolve_requested_provider(version, policy, args.core_binary)
    invocation = provider.command + [
        "init",
        "--project",
        str(project),
        "--database",
        root,
        "--format",
        "json",
    ]
    if args.allow_nonempty:
        invocation.append("--allow-nonempty")
    completed = _run(invocation)
    if completed.returncode != 0:
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        return completed.returncode

    try:
        configured = configured_database(project)
        database = project / ".nostdb" / configured
        if configured != root or not database.is_file():
            raise ConfigError("Core did not create {}".format(database))
        skills = {
            "core_provider": policy,
            "core_version": version,
        }
        if args.core_binary:
            skills["core_binary"] = args.core_binary
        original = read_text(project)
        updated = update_sections(original, {"skills": skills})
        atomic_write(config_path(project), updated, expected_text=original)
    except ConfigConflictError:
        raise
    except (ConfigError, OSError):
        _cleanup_init(project, root)
        raise

    sys.stderr.write(completed.stderr)
    print(
        json.dumps(
            {
                "core_version": version,
                "root": root,
                "settings": str(config_path(project)),
                "source_enabled": False,
                "src": str(project),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def update(args: argparse.Namespace) -> int:
    project = args.src.expanduser().resolve()
    provider = resolve_provider(project, args.core_binary)
    links = refresh_links(project)
    completed = _run(
        provider.command
        + [
            "update",
            "--project",
            str(project),
            "--format",
            "json",
        ]
    )
    if completed.returncode != 0:
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        return completed.returncode
    try:
        native = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise CoreResolutionError(
            "native update returned invalid JSON: {}".format(error)
        ) from error
    sys.stderr.write(completed.stderr)
    print(
        json.dumps(
            {
                "core_version": provider.version,
                "links": links,
                "root": configured_database(project),
                "src": str(project),
                "updated": native,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="initialize through the native CLI")
    init.add_argument("--src", type=Path, required=True)
    init.add_argument("--core-version", default=DEFAULT_CORE_VERSION)
    init.add_argument("--core-provider", choices=CORE_PROVIDERS, default="auto")
    init.add_argument("--core-binary")
    init.add_argument("--root", default="root.nostdb")
    init.add_argument("--allow-nonempty", action="store_true")
    init.set_defaults(handler=initialize)
    update_command = commands.add_parser(
        "update", help="refresh nested project links and synchronize all roots"
    )
    update_command.add_argument("--src", type=Path, required=True)
    update_command.add_argument("--core-binary")
    update_command.set_defaults(handler=update)
    remove_command = commands.add_parser(
        "remove", help="delete guarded project-local NostDB directories"
    )
    remove_command.add_argument("--src", type=Path, required=True)
    remove_command.add_argument("--dry-run", action="store_true")
    remove_command.set_defaults(handler=remove)
    return root


def main(arguments: Optional[list] = None) -> int:
    """Dispatch one guarded public Skill mutation."""

    try:
        args = parser().parse_args(arguments)
        result = args.handler(args)
        if isinstance(result, dict):
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
            return 0
        return result
    except (ConfigError, CoreResolutionError, OSError) as error:
        print("nostdb-skill: {}".format(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
