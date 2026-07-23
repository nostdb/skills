#!/usr/bin/env python3
"""Emit one deterministic source-provenance comment for a declaration."""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--kind", choices=("document", "code"), required=True)
    parser.add_argument("--locator", required=True)
    parser.add_argument("--source-label")
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    project = args.project.resolve()
    source = args.source.resolve()
    try:
        payload = source.read_bytes()
    except OSError as error:
        print("nostdb-provenance: cannot read {}: {}".format(source, error), file=sys.stderr)
        return 7
    if args.source_label:
        label = args.source_label
    else:
        try:
            label = source.relative_to(project).as_posix()
        except ValueError:
            print(
                "nostdb-provenance: external sources require --source-label to avoid absolute paths",
                file=sys.stderr,
            )
            return 2
    if not label or label.startswith("/") or ".." in Path(label).parts or "\n" in label or "\r" in label:
        print("nostdb-provenance: source label must be a normalized relative path", file=sys.stderr)
        return 2
    source_hash = hashlib.sha256(payload).hexdigest()
    if args.expected_sha256 and args.expected_sha256 != source_hash:
        print(
            "nostdb-provenance: source conflict: expected {}, found {}".format(
                args.expected_sha256, source_hash
            ),
            file=sys.stderr,
        )
        return 6
    record = {
        "kind": args.kind,
        "locator": args.locator,
        "sha256": source_hash,
        "source": label,
    }
    print("// @provenance " + json.dumps(record, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
