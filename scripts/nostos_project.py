#!/usr/bin/env python3
"""Initialize and configure a portable Nostos Source Mode project."""

import argparse
import json
import sys
import uuid
from pathlib import Path

from nostos_config import (
    ConfigError,
    atomic_write,
    config_path,
    layout_source,
    read_text,
    update_sections,
    validate_core_version,
    validate_database_path,
    validate_module_id,
)


DEFAULT_CORE_VERSION = "0.1.0"


def initialize(args: argparse.Namespace) -> dict:
    project = args.project.resolve()
    source_relative = layout_source(args.layout)
    source = project / source_relative
    configuration = config_path(project)
    if configuration.exists():
        raise ConfigError("refusing to replace existing {}".format(configuration))
    if source.exists():
        raise ConfigError("refusing to replace existing {}".format(source))
    if project.exists() and any(project.iterdir()) and not args.allow_nonempty:
        raise ConfigError(
            "refusing to initialize a nonempty directory without --allow-nonempty: {}".format(
                project
            )
        )
    module_id = validate_module_id(args.module_id or str(uuid.uuid4()))
    validate_core_version(args.core_version)
    validate_database_path(args.database)
    project.mkdir(parents=True, exist_ok=True)
    source.parent.mkdir(parents=True, exist_ok=True)
    core_binary = ""
    if args.core_binary:
        core_binary = 'core_binary = {}\n'.format(json.dumps(args.core_binary, ensure_ascii=False))
    text = (
        'config_version = 1\n'
        'language_version = 1\n\n'
        '[source]\n'
        'layout = {layout}\n'
        'entry = {entry}\n\n'
        '[modules]\n'
        '{entry} = {module_id}\n\n'
        '[skills]\n'
        'core_version = {core_version}\n'
        'database = {database}\n'
        '{core_binary}'
    ).format(
        layout=json.dumps(args.layout),
        entry=json.dumps(source_relative),
        module_id=json.dumps(module_id),
        core_version=json.dumps(args.core_version),
        database=json.dumps(args.database),
        core_binary=core_binary,
    )
    created_source = False
    try:
        with source.open("x", encoding="utf-8", newline="\n") as output:
            output.write("// NostosDB source\n")
        created_source = True
        atomic_write(configuration, text)
    except BaseException:
        if created_source:
            source.unlink(missing_ok=True)
        raise
    return {
        "config": str(configuration),
        "core_version": args.core_version,
        "layout": args.layout,
        "module_id": module_id,
        "source": source_relative,
    }


def configure(args: argparse.Namespace) -> dict:
    project = args.project.resolve()
    updates = {}
    if args.layout:
        layout_source(args.layout)
        updates.setdefault("source", {})["layout"] = args.layout
    skills = {}
    if args.core_version:
        skills["core_version"] = validate_core_version(args.core_version)
    if args.core_binary:
        skills["core_binary"] = args.core_binary
    if args.database:
        skills["database"] = validate_database_path(args.database)
    if skills:
        updates["skills"] = skills
    if not updates:
        raise ConfigError("configure requires at least one value")
    updated = update_sections(read_text(project), updates)
    atomic_write(config_path(project), updated)
    return {"config": str(config_path(project)), "updated": updates}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a new Source Mode project")
    init.add_argument("--project", type=Path, required=True)
    init.add_argument("--layout", choices=("centralized", "colocated", "single"), required=True)
    init.add_argument("--core-version", default=DEFAULT_CORE_VERSION)
    init.add_argument("--core-binary")
    init.add_argument("--database", default="graph.ndb")
    init.add_argument("--module-id")
    init.add_argument("--allow-nonempty", action="store_true")
    init.set_defaults(handler=initialize)
    change = commands.add_parser("configure", help="persist layout and Core selection")
    change.add_argument("--project", type=Path, required=True)
    change.add_argument("--layout", choices=("centralized", "colocated", "single"))
    change.add_argument("--core-version")
    change.add_argument("--core-binary")
    change.add_argument("--database")
    change.set_defaults(handler=configure)
    return root


def main() -> int:
    try:
        result = parser().parse_args()
        print(json.dumps(result.handler(result), sort_keys=True, separators=(",", ":")))
        return 0
    except (ConfigError, OSError) as error:
        print("nostos-project: {}".format(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
