#!/usr/bin/env python3
"""Resolve and run an exactly pinned native or npx Nostos CLI provider."""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from nostos_config import ConfigError
from nostos_provider import (
    CoreResolutionError,
    native_command,
    npx_command,
    provider_payload,
    resolve_provider,
    run_command,
)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    locate = commands.add_parser("resolve", help="print the compatible CLI provider")
    locate.add_argument("--project", type=Path, required=True)
    locate.add_argument("--binary")
    locate.add_argument("--json", action="store_true")
    run = commands.add_parser("run", help="run the compatible CLI provider")
    run.add_argument("--project", type=Path, required=True)
    run.add_argument("--binary")
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        provider = resolve_provider(args.project, args.binary)
        if args.command == "resolve":
            if args.json:
                print(json.dumps(provider_payload(provider, args.project), sort_keys=True))
            elif provider.binary:
                print(provider.binary)
            else:
                print(json.dumps(provider.command, separators=(",", ":")))
            return 0
        arguments: List[str] = list(args.arguments)
        if arguments and arguments[0] == "--":
            arguments.pop(0)
        if not arguments:
            raise CoreResolutionError("run requires arguments after --")
        return run_command(provider.command + arguments)
    except (ConfigError, CoreResolutionError) as error:
        print("nostos-core: {}".format(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
