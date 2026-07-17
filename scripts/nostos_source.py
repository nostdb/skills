#!/usr/bin/env python3
"""Hash or conflict-safely install one complete canonical .nostos file."""

import argparse
import hashlib
import json
import os
import re
import socket
import sys
import tempfile
from pathlib import Path


DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceError(RuntimeError):
    """A source input or conflict failure."""


def read_source(path: Path) -> bytes:
    if path.is_symlink() or path.suffix != ".nostos" or not path.is_file():
        raise SourceError("source target must be one existing non-symlink .nostos file")
    data = path.read_bytes()
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SourceError("source is not UTF-8: {}".format(path)) from error
    return data


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def temporary_bytes(parent: Path, prefix: str, data: bytes, mode: int) -> Path:
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


def install(target: Path, candidate: Path, expected: str) -> dict:
    target = target.absolute()
    candidate = candidate.resolve()
    if not DIGEST_RE.fullmatch(expected):
        raise SourceError("--expected-sha256 must be 64 lowercase hexadecimal characters")
    if candidate.suffix == ".ndb" or not candidate.is_file():
        raise SourceError("candidate must be a regular text file and never an .ndb file")
    replacement = candidate.read_bytes()
    try:
        replacement.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SourceError("candidate is not UTF-8") from error
    if replacement and not replacement.endswith(b"\n"):
        raise SourceError("candidate must end with a newline")
    lock_path = target.with_name("." + target.name + ".nostos-lock")
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
        if target.is_symlink() or target.suffix != ".nostos":
            raise SourceError("source target must be one existing non-symlink .nostos file")
        with target.open("rb") as original_file:
            original_stat = os.fstat(original_file.fileno())
            original = original_file.read()
            if digest(original) != expected:
                raise SourceError("source conflict: {} changed before installation".format(target))
            mode = original_stat.st_mode & 0o777
            temporary_path = temporary_bytes(target.parent, ".nostos-source-", replacement, mode)
            current_stat = target.stat()
            original_file.seek(0)
            before_replace = original_file.read()
            if not os.path.samestat(original_stat, current_stat) or digest(before_replace) != expected:
                raise SourceError("source conflict: {} changed during installation".format(target))
            os.replace(str(temporary_path), str(target))
            temporary_path = None
            original_file.seek(0)
            raced_content = original_file.read()
            if digest(raced_content) != expected:
                if digest(read_source(target)) == digest(replacement):
                    restore = temporary_bytes(target.parent, ".nostos-restore-", raced_content, mode)
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
    if target.suffix != ".nostos":
        raise SourceError("source target must end in .nostos")
    lock_path = target.with_name("." + target.name + ".nostos-lock")
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
        print("nostos-source: {}".format(error), file=sys.stderr)
        return code


if __name__ == "__main__":
    sys.exit(main())
