#!/usr/bin/env python3
"""Hash or conflict-safely install one complete canonical .nost file."""

import argparse
import hashlib
import json
import os
import re
import socket
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional


DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceError(RuntimeError):
    """A source input or conflict failure."""


def read_source(path: Path) -> bytes:
    if path.is_symlink() or path.suffix != ".nost" or not path.is_file():
        raise SourceError("source target must be one existing non-symlink .nost file")
    data = path.read_bytes()
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SourceError("source is not UTF-8: {}".format(path)) from error
    return data


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def temporary_bytes(parent: Path, prefix: str, data: bytes, mode: int) -> Path:
    """Create and durably fill one exclusive same-directory temporary file."""

    descriptor, temporary = tempfile.mkstemp(prefix=prefix, dir=str(parent))
    path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(str(path), mode)
        return path
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def install(
    target: Path,
    candidate: Path,
    expected: str,
    _before_replace: Optional[Callable[[], None]] = None,
) -> dict:
    target = target.absolute()
    candidate = candidate.resolve()
    if not DIGEST_RE.fullmatch(expected):
        raise SourceError("--expected-sha256 must be 64 lowercase hexadecimal characters")
    if candidate.suffix == ".nostdb" or not candidate.is_file():
        raise SourceError("candidate must be a regular text file and never an .nostdb file")
    replacement = candidate.read_bytes()
    try:
        replacement.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SourceError("candidate is not UTF-8") from error
    if replacement and not replacement.endswith(b"\n"):
        raise SourceError("candidate must end with a newline")
    lock_path = target.with_name("." + target.name + ".nost-lock")
    try:
        lock_descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise SourceError(
            "source conflict: another guarded edit is active for {}; use unlock only after verifying it is stale"
            .format(target)
        ) from error
    with os.fdopen(lock_descriptor, "w", encoding="utf-8") as lock_file:
        json.dump({"host": socket.gethostname(), "pid": os.getpid()}, lock_file, sort_keys=True)
        lock_file.write("\n")
        lock_file.flush()
        os.fsync(lock_file.fileno())
    temporary_path = None
    try:
        if target.is_symlink() or target.suffix != ".nost":
            raise SourceError("source target must be one existing non-symlink .nost file")
        with target.open("rb") as original_file:
            original_stat = os.fstat(original_file.fileno())
            original = original_file.read()
            if digest(original) != expected:
                raise SourceError("source conflict: {} changed before installation".format(target))
            mode = original_stat.st_mode & 0o777
            temporary_path = temporary_bytes(target.parent, ".nost-source-", replacement, mode)
            with target.open("rb") as checked_file:
                checked_stat = os.fstat(checked_file.fileno())
                checked_content = checked_file.read()
                checked_path_stat = target.stat()
                if (
                    target.is_symlink()
                    or not os.path.samestat(original_stat, checked_stat)
                    or not os.path.samestat(checked_stat, checked_path_stat)
                    or digest(checked_content) != expected
                ):
                    raise SourceError(
                        "source conflict: {} changed during installation".format(target)
                    )
            if _before_replace is not None:
                _before_replace()
            # Reopen, hash, and bind the path to the descriptor immediately before
            # the atomic namespace replacement. This keeps the unavoidable
            # portable stat-to-replace interval independent of file size.
            with target.open("rb") as replace_file:
                replace_stat = os.fstat(replace_file.fileno())
                before_replace = replace_file.read()
                replace_path_stat = target.stat()
                if (
                    target.is_symlink()
                    or not os.path.samestat(original_stat, replace_stat)
                    or not os.path.samestat(replace_stat, replace_path_stat)
                    or digest(before_replace) != expected
                ):
                    raise SourceError(
                        "source conflict: {} changed immediately before replacement"
                        .format(target)
                    )
                os.replace(str(temporary_path), str(target))
                temporary_path = None
                replace_file.seek(0)
                raced_content = replace_file.read()
                if digest(raced_content) != expected:
                    if digest(read_source(target)) == digest(replacement):
                        restore = temporary_bytes(
                            target.parent, ".nost-restore-", raced_content, mode
                        )
                        try:
                            os.replace(str(restore), str(target))
                        finally:
                            restore.unlink(missing_ok=True)
                    raise SourceError(
                        "source conflict: {} changed during atomic replacement; external content was restored"
                        .format(target)
                    )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        lock_path.unlink(missing_ok=True)
    return {"path": str(target), "sha256": digest(replacement)}


def unlock(target: Path) -> dict:
    target = target.absolute()
    if target.suffix != ".nost":
        raise SourceError("source target must end in .nost")
    lock_path = target.with_name("." + target.name + ".nost-lock")
    try:
        owner = json.loads(lock_path.read_text(encoding="utf-8"))
        host = owner["host"]
        pid = owner["pid"]
    except FileNotFoundError as error:
        raise SourceError("no guarded-edit lock exists for {}".format(target)) from error
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise SourceError("lock metadata is invalid; inspect manually: {}".format(lock_path)) from error
    if host != socket.gethostname() or not isinstance(pid, int) or pid <= 0:
        raise SourceError("lock owner cannot be verified on this host: {}".format(lock_path))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        lock_path.unlink()
        return {"path": str(target), "removed_stale_pid": pid}
    except PermissionError:
        pass
    raise SourceError("guarded edit is still active for {} (pid {})".format(target, pid))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    hash_command = commands.add_parser("hash", help="hash one current source file")
    hash_command.add_argument("--file", type=Path, required=True)
    write = commands.add_parser("install", help="install a complete source after a hash guard")
    write.add_argument("--file", type=Path, required=True)
    write.add_argument("--from", dest="candidate", type=Path, required=True)
    write.add_argument("--expected-sha256", required=True)
    unlock_command = commands.add_parser("unlock", help="remove a verified stale same-host lock")
    unlock_command.add_argument("--file", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "hash":
            print(digest(read_source(args.file.absolute())))
        elif args.command == "unlock":
            print(json.dumps(unlock(args.file), sort_keys=True, separators=(",", ":")))
        else:
            print(
                json.dumps(
                    install(args.file, args.candidate, args.expected_sha256),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        return 0
    except (OSError, SourceError) as error:
        code = 6 if "source conflict:" in str(error) else 7
        print("nostdb-source: {}".format(error), file=sys.stderr)
        return code


if __name__ == "__main__":
    sys.exit(main())
