#!/usr/bin/env python3
"""Bridge guarded Skill init/remove actions to the native NostDB CLI."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from nostdb_config import (
    CORE_PROVIDERS,
    ConfigConflictError,
    ConfigError,
    atomic_write,
    config_path,
    read_text,
    update_sections,
    validate_core_provider,
    validate_core_version,
)
from nostdb_project import DEFAULT_CORE_VERSION, initialize as initialize_config, remove
from nostdb_provider import (
    CoreProvider,
    CoreResolutionError,
    resolve_requested_provider,
)

LEGACY_NPX_WITHOUT_NATIVE_INIT = frozenset({"0.0.2"})


def _cleanup_init(project: Path) -> None:
    configuration = config_path(project)
    database = project / ".nostdb"
    try:
        configuration.unlink()
    except FileNotFoundError:
        pass
    for suffix in ("", ".lock", "-wal", "-shm", "-journal"):
        try:
            Path(str(database) + suffix).unlink()
        except FileNotFoundError:
            pass


def _run(command: list) -> subprocess.CompletedProcess:
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


def _supports_native_init(provider: CoreProvider) -> bool:
    if (
        provider.kind == "npx"
        and provider.version in LEGACY_NPX_WITHOUT_NATIVE_INIT
    ):
        return False
    return _run(provider.command + ["init", "--help"]).returncode == 0


def _initialize_with_native(
    args: argparse.Namespace, command: list, project: Path
) -> subprocess.CompletedProcess:
    invocation = command + [
        "init",
        "--project",
        str(project),
        "--format",
        "json",
    ]
    if args.allow_nonempty:
        invocation.append("--allow-nonempty")
    return _run(invocation)


def _initialize_with_legacy_cli(
    args: argparse.Namespace, command: list, project: Path
) -> subprocess.CompletedProcess:
    initialize_config(args)
    completed = _run(
        command
        + [
            "sync",
            "--project",
            str(project),
            "--format",
            "json",
        ]
    )
    if completed.returncode != 0:
        _cleanup_init(project)
    return completed


def initialize(args: argparse.Namespace) -> int:
    project = args.src.expanduser().resolve()
    version = validate_core_version(args.core_version)
    policy = validate_core_provider(args.core_provider)
    provider = resolve_requested_provider(version, policy, args.core_binary)
    uses_native_init = _supports_native_init(provider)
    if uses_native_init:
        completed = _initialize_with_native(args, provider.command, project)
    else:
        completed = _initialize_with_legacy_cli(args, provider.command, project)
    if completed.returncode != 0:
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        return completed.returncode

    database = project / ".nostdb"
    try:
        if not database.is_file():
            raise ConfigError("Core did not create {}".format(database))
        if uses_native_init:
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
        _cleanup_init(project)
        raise

    sys.stderr.write(completed.stderr)
    print(
        json.dumps(
            {
                "config": str(config_path(project)),
                "core_version": version,
                "nost": False,
                "root": ".nostdb",
                "src": str(project),
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
    init.add_argument("--allow-nonempty", action="store_true")
    init.set_defaults(handler=initialize)
    remove_command = commands.add_parser(
        "remove", help="delete guarded project-local NostDB files"
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
