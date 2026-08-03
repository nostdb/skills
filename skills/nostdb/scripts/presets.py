#!/usr/bin/env python3
"""The presets this Skill ships, and which one covers an annotation the Engine did not read.

Answered from this Skill's own files and without an Engine: a preset is part of the Skill, and asking somebody
to install a database to find out which presets exist is the wrong order of operations.

The Spring Boot Skill ships its own copy of this, and has to. An installer copies a skill folder, so anything
a definition reaches outside its own folder is absent once installed — the repository verifier enforces that,
and a shared script would be a Skill that worked in this repository and failed everywhere else.

# Python rather than `/bin/sh`

This read a table and matched a name, and shell has no data structures for either: the index is pipe separated
precisely because a shell reader could not be trusted with JSON, and every field access went through `awk`.
Python reads the same file in a `split` and matches on a set.

The index format did not change with the language. It is still four pipe-separated fields, because it is a
document a person edits and a reader in any language can take.

# What a preset is, and what it is not

A preset is a **vocabulary** — the names a proposal uses once something else has read the source — and a
**validation target**, because it is a `.nost` document the Engine checks like any other. It is not an
analyzer: nothing here reads `@Entity`, and nothing here may derive a fact from one.

That line is the whole boundary. Deriving facts from a preset without a model would make this Skill a second
analyzer, reading annotations the Engine's own analyzers do not read, which is exactly what the root
contract's rule about an AI-free action having the CLI do the work prevents.

# A preset an annotation does not select
#
# Most presets are chosen by an annotation the Engine reported and did not read. One is not: a project's name
# and purpose exist whether or not the project has annotations. The index marks that with `*`, this reader
# reports it through `always`, and `for` never matches it — `*` is not an annotation, so a vocabulary that
# applies everywhere is not one an annotation can claim.

Usage:
  presets.py                 every preset, with what it covers
  presets.py always          the presets that apply to every project
  presets.py document NAME   the path to one preset's `.nost`, for the Engine to check
  presets.py for NAME        which preset covers an annotation name, if any

Exit codes: 0 answered, 1 nothing matched, 2 used incorrectly.
"""

from __future__ import annotations

import sys
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
INDEX = FOLDER / "presets" / "index"

FIELDS = ("name", "document", "covers", "describes")

# What the `covers` column holds when a preset is selected by nothing.
ALWAYS = "*"


class Preset:
    """One row of the index."""

    def __init__(self, name: str, document: str, covers: str, describes: str) -> None:
        self.name = name
        self.document = document
        self.describes = describes
        # `*` is a marker rather than a name, so it leaves `covers` empty: every membership test against it
        # then answers no, which is what keeps `for` from claiming this preset for an annotation.
        self.always = covers.strip() == ALWAYS
        # A set, so a lookup is a membership test on the whole name. Matching a substring would claim a preset
        # for an annotation nobody wrote a schema for, and this index holds pairs where one name is a prefix of
        # another — `Min` and `DecimalMin`, `Valid` and `Validated`.
        self.covers = (
            set()
            if self.always
            else {held.strip() for held in covers.split(",") if held.strip()}
        )

    @property
    def covers_in_order(self) -> str:
        if self.always:
            return "every project; no annotation selects it"
        return ", ".join(sorted(self.covers))


def read_index() -> list[Preset]:
    """Every row, comments and blank lines dropped.

    One place, so no caller re-derives the format. A row with the wrong number of fields is a malformed index
    rather than a row to skip: skipping one would answer "no preset covers that" for an annotation a preset
    does cover, which is the same as being wrong quietly.
    """
    if not INDEX.is_file():
        fail(f"{INDEX.name} is not beside this script", 2)
    presets = []
    for number, line in enumerate(INDEX.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        parts = [part.strip() for part in text.split("|")]
        if len(parts) != len(FIELDS):
            fail(
                f"{INDEX.name}:{number}: a row has {len(parts)} fields, not "
                f"{len(FIELDS)} ({', '.join(FIELDS)})",
                2,
            )
        if not all(parts):
            fail(f"{INDEX.name}:{number}: a row has an empty field", 2)
        presets.append(Preset(*parts))
    if not presets:
        fail(f"{INDEX.name} declares no preset", 2)
    return presets


def fail(message: str, code: int) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def command_list(presets: list[Preset]) -> None:
    for preset in presets:
        print(preset.name)
        print(f"  {preset.describes}")
        print(f"  covers: {preset.covers_in_order}")
        print(f"  schema: presets/{preset.document}")


def command_document(presets: list[Preset], wanted: str) -> None:
    for preset in presets:
        if preset.name == wanted:
            print(f"presets/{preset.document}")
            return
    fail(f"no preset named {wanted}", 1)


def command_always(presets: list[Preset]) -> None:
    """The presets that apply whatever the Engine reported.

    Exiting 1 when there are none is an answer rather than a failure, the way `for` reports a miss.
    """
    found = [preset for preset in presets if preset.always]
    if not found:
        fail("no preset applies to every project", 1)
    for preset in found:
        print(preset.name)


def command_for(presets: list[Preset], annotation: str) -> None:
    """Which preset covers an annotation the Engine reported uninterpreted.

    Exiting 1 is an answer rather than a failure. A build reports every annotation no analyzer read, and most
    of them mean nothing to any preset here, and another Skill may cover what this one does not.
    """
    if annotation == ALWAYS:
        fail(f"{ALWAYS} is not an annotation name; use `presets.py always`", 2)
    for preset in presets:
        if annotation in preset.covers:
            print(preset.name)
            return
    fail(f"no preset covers {annotation}", 1)


def main(argv: list[str]) -> None:
    action = argv[0] if argv else "list"
    presets = read_index()
    if action == "list":
        if len(argv) > 1:
            fail("usage: presets.py list", 2)
        command_list(presets)
    elif action == "always":
        if len(argv) > 1:
            fail("usage: presets.py always", 2)
        command_always(presets)
    elif action == "document":
        if len(argv) != 2:
            fail("usage: presets.py document NAME", 2)
        command_document(presets, argv[1])
    elif action == "for":
        if len(argv) != 2:
            fail("usage: presets.py for ANNOTATION", 2)
        command_for(presets, argv[1])
    else:
        fail("usage: presets.py [list | always | document NAME | for ANNOTATION]", 2)


if __name__ == "__main__":
    main(sys.argv[1:])
