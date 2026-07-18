#!/usr/bin/env python3
"""Resolve and run an exactly pinned native or npx Nostos CLI provider."""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence

from nostos_config import (
    ConfigError,
    require_core_version,
    skill_values,
    validate_core_provider,
)


VERSION_OUTPUT = re.compile(
    r"^nostos ([0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?)$"
)
NPM_PACKAGE = "@nostosdb/cli"


class CoreResolutionError(RuntimeError):
    """A missing or incompatible public CLI boundary."""


class CoreProvider(NamedTuple):
    """One shell-free command prefix for invoking the pinned CLI."""

    kind: str
    command: List[str]
    version: str
    binary_path: Optional[str]

    @property
    def binary(self) -> Optional[str]:
        """Return the native binary path, or None for npx."""

        return self.binary_path


def native_candidate(project: Path, explicit: Optional[str]) -> Optional[Path]:
    """Select one native candidate without validating its version."""

    configured = skill_values(project).get("core_binary")
    selected = explicit or os.environ.get("NOSTOS_BIN") or configured
    if selected:
        candidate = Path(selected)
        if not candidate.is_absolute():
            candidate = project / candidate
        return candidate.resolve()
    located = shutil.which("nostos")
    return Path(located).resolve() if located else None


def checked_version(command: Sequence[str], expected: str, label: str) -> None:
    """Require one command prefix to report the exact pinned version."""

    try:
        completed = subprocess.run(
            list(command) + ["--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CoreResolutionError("cannot execute {}: {}".format(label, error)) from error
    output = completed.stdout.strip()
    match = VERSION_OUTPUT.fullmatch(output)
    if completed.returncode != 0 or match is None:
        detail = completed.stderr.strip() or output or "no version output"
        raise CoreResolutionError(
            "invalid nostos --version response from {}: {}".format(label, detail)
        )
    actual = match.group(1)
    if actual != expected:
        raise CoreResolutionError(
            "Core version mismatch: expected {} from nostos.toml, found {} at {}".format(
                expected, actual, label
            )
        )


def native_provider(candidate: Path, expected: str) -> CoreProvider:
    """Validate one selected native CLI."""

    if not candidate.is_file():
        raise CoreResolutionError(
            "configured Core binary does not exist: {}".format(candidate)
        )
    command = native_command(candidate)
    checked_version(command, expected, str(candidate))
    return CoreProvider("native", command, expected, str(candidate))


def native_command(candidate: Path, windows: Optional[bool] = None) -> List[str]:
    """Avoid a command shell when an npm-installed Windows shim is selected."""

    if windows is None:
        windows = os.name == "nt"
    if not windows or candidate.suffix.lower() not in {".cmd", ".bat"}:
        return [str(candidate)]
    node = shutil.which("node")
    package = Path("@nostosdb") / "cli" / "bin" / "nostos.js"
    possible = [
        candidate.parent / "node_modules" / package,
        candidate.parent.parent / package,
    ]
    launcher = next((path.resolve() for path in possible if path.is_file()), None)
    if node is None or launcher is None:
        raise CoreResolutionError(
            "cannot safely execute npm Windows shim without its Node launcher: {}"
            .format(candidate)
        )
    return [str(Path(node).resolve()), str(launcher)]


def npx_command(
    windows: Optional[bool] = None, located: Optional[str] = None
) -> List[str]:
    """Locate npx without invoking a Windows batch file through a shell."""

    if windows is None:
        windows = os.name == "nt"
    if located is None:
        located = shutil.which("npx")
    if located is None:
        return []
    path = Path(located)
    if not windows or path.suffix.lower() not in {".cmd", ".bat"}:
        return [str(path.resolve())]
    node = shutil.which("node")
    cli = path.parent / "node_modules" / "npm" / "bin" / "npx-cli.js"
    if node is None or not cli.is_file():
        raise CoreResolutionError(
            "cannot safely execute npx Windows shim without its Node CLI"
        )
    return [str(Path(node).resolve()), str(cli.resolve())]


def npx_provider(expected: str) -> CoreProvider:
    """Validate the pinned official npm package through npx."""

    command = npx_command()
    if not command:
        raise CoreResolutionError(
            "cannot locate npx for nostos {}; install @nostosdb/cli with npm, "
            "Homebrew, or a direct artifact".format(expected)
        )
    command.extend(
        [
            "--yes",
            "--package={}@{}".format(NPM_PACKAGE, expected),
            "nostos",
        ]
    )
    try:
        checked_version(command, expected, "{}@{} via npx".format(NPM_PACKAGE, expected))
    except CoreResolutionError as error:
        raise CoreResolutionError(
            "{}; verify npm cache or network access, or install the pinned CLI"
            .format(error)
        ) from error
    return CoreProvider("npx", command, expected, None)


def resolve_provider(
    project: Path, explicit: Optional[str] = None
) -> CoreProvider:
    """Resolve the project-selected native or npx provider."""

    project = project.resolve()
    values = skill_values(project)
    expected = require_core_version(project)
    policy = validate_core_provider(values.get("core_provider", "installed"))
    if policy == "npx":
        if explicit:
            raise CoreResolutionError(
                "--binary cannot be combined with skills.core_provider npx"
            )
        return npx_provider(expected)
    candidate = native_candidate(project, explicit)
    if candidate is not None:
        return native_provider(candidate, expected)
    if policy == "auto":
        return npx_provider(expected)
    raise CoreResolutionError(
        "cannot locate nostos {}; set skills.core_binary, NOSTOS_BIN, or PATH, "
        "or configure skills.core_provider = \"auto\" for pinned npx fallback"
        .format(expected)
    )


def resolve(project: Path, explicit: Optional[str] = None) -> Path:
    """Backward-compatible native-only resolver used by existing integrations."""

    provider = resolve_provider(project, explicit)
    if provider.binary is None:
        raise CoreResolutionError(
            "resolved npx provider has no persistent binary path; use resolve --json"
        )
    return Path(provider.binary)


def run_command(command: Sequence[str]) -> int:
    """Run one provider command and forward termination signals."""

    try:
        child = subprocess.Popen(list(command))
    except OSError as error:
        raise CoreResolutionError(
            "cannot execute Core provider {}: {}".format(command[0], error)
        ) from error
    previous = {}

    def forward(signum, _frame):
        if child.poll() is None:
            child.send_signal(signum)

    forwarded = [signal.SIGINT, signal.SIGTERM]
    try:
        for signum in forwarded:
            previous[signum] = signal.signal(signum, forward)
        result = child.wait()
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    if result < 0 and os.name != "nt":
        signum = -result
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
    return result


def provider_payload(provider: CoreProvider, project: Path) -> dict:
    """Render deterministic provider metadata."""

    values = skill_values(project)
    return {
        "binary": provider.binary,
        "command": provider.command,
        "database": values.get("database"),
        "provider": provider.kind,
        "version": provider.version,
    }


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
