#!/usr/bin/env python3
"""Run a strictly read-only Nostos CLI surface for graph visualization."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from nostos_config import ConfigError, skill_values
from nostos_provider import (
    CoreProvider,
    CoreResolutionError,
    native_provider,
    resolve_provider,
    run_command,
)


DEFAULT_CORE_VERSION = "0.0.1"
FORMATS = {"table", "json", "jsonl", "csv"}
INSPECTION_COMMANDS = {"check", "inspect", "schema", "stats", "unresolved"}


class VisualizationError(RuntimeError):
    """An unsafe or malformed visualization-only request."""


def option_value(arguments: List[str], index: int, option: str) -> str:
    try:
        return arguments[index + 1]
    except IndexError as error:
        raise VisualizationError("{} requires a value".format(option)) from error


def safe_query(arguments: List[str], database: Path) -> List[str]:
    query: Optional[str] = None
    output_format = "json"
    read_only = False
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--read-only":
            if read_only:
                raise VisualizationError("--read-only may be provided only once")
            read_only = True
        elif argument == "--format":
            output_format = option_value(arguments, index, argument)
            index += 1
        elif argument.startswith("-"):
            raise VisualizationError(
                "query option {} is not allowed by nostos-visualize".format(argument)
            )
        elif query is None:
            query = argument
        else:
            raise VisualizationError("only one inline visualization query is allowed")
        index += 1
    if not read_only:
        raise VisualizationError("visualization query requires --read-only")
    if query is None:
        raise VisualizationError("visualization query requires inline Cypher")
    if output_format not in FORMATS:
        raise VisualizationError("unsupported output format {}".format(output_format))
    return [
        "query",
        query,
        "--read-only",
        "--database",
        str(database),
        "--format",
        output_format,
    ]


def safe_inspection(command: str, arguments: List[str], database: Path) -> List[str]:
    output_format = "json"
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument != "--format":
            raise VisualizationError(
                "{} option {} is not allowed by nostos-visualize".format(
                    command, argument
                )
            )
        output_format = option_value(arguments, index, argument)
        index += 2
    if output_format not in FORMATS:
        raise VisualizationError("unsupported output format {}".format(output_format))
    return [command, "--database", str(database), "--format", output_format]


def safe_command(arguments: List[str], database: Path) -> List[str]:
    if arguments and arguments[0] == "--":
        arguments.pop(0)
    if not arguments:
        raise VisualizationError("run requires a read-only command after --")
    command = arguments.pop(0)
    if command == "query":
        return safe_query(arguments, database)
    if command in INSPECTION_COMMANDS:
        return safe_inspection(command, arguments, database)
    raise VisualizationError(
        "command {} is not available in the read-only visualization wrapper".format(
            command
        )
    )


def existing_database(path: Path) -> Path:
    absolute = path.absolute()
    if absolute.is_symlink() or absolute.suffix != ".ndb" or not absolute.is_file():
        raise VisualizationError(
            "--database must name one existing non-symlink .ndb file"
        )
    return absolute.resolve()


def select_provider(project: Optional[Path], explicit: Optional[str]) -> CoreProvider:
    if project is not None:
        return resolve_provider(project, explicit)
    if not explicit:
        raise CoreResolutionError(
            "standalone visualization requires an explicit --binary PATH"
        )
    candidate = Path(explicit)
    if not candidate.is_absolute():
        candidate = Path(os.getcwd()) / candidate
    return native_provider(candidate.resolve(), DEFAULT_CORE_VERSION)


def provider_json(
    provider: CoreProvider, project: Optional[Path], database: Optional[Path]
) -> dict:
    configured_database = None
    if project is not None:
        configured_database = skill_values(project).get("database")
    return {
        "binary": provider.binary,
        "command": provider.command,
        "database": str(database) if database is not None else configured_database,
        "provider": provider.kind,
        "read_only": True,
        "version": provider.version,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    locate = commands.add_parser("resolve", help="print the compatible CLI provider")
    locate.add_argument("--project", type=Path)
    locate.add_argument("--binary")
    locate.add_argument("--database", type=Path)
    locate.add_argument("--json", action="store_true")
    run = commands.add_parser("run", help="run one allowlisted read-only command")
    run.add_argument("--project", type=Path)
    run.add_argument("--binary")
    run.add_argument("--database", type=Path, required=True)
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "run":
            database = existing_database(args.database)
            arguments = safe_command(list(args.arguments), database)
            provider = select_provider(args.project, args.binary)
            return run_command(provider.command + arguments)
        database = existing_database(args.database) if args.database else None
        provider = select_provider(args.project, args.binary)
        if args.json:
            print(
                json.dumps(
                    provider_json(provider, args.project, database), sort_keys=True
                )
            )
        elif provider.binary:
            print(provider.binary)
        else:
            print(json.dumps(provider.command, separators=(",", ":")))
        return 0
    except (ConfigError, CoreResolutionError, VisualizationError) as error:
        print("nostos-visualize: {}".format(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
