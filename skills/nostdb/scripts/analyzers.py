#!/usr/bin/env python3
"""The `nostdb-analyzer-*` Skills installed beside this one, and the announcement for using one.

A vocabulary for one framework is its own Skill — `nostdb-analyzer-springboot` is the first — because a
framework a project does not use is a document nobody should have to install. This finds the ones that are
installed, so `/nostdb` can use a better vocabulary when one is present and say so when it does.

# Discovered, never referenced

An installer copies a skill *folder*, so anything a definition reaches outside its own is absent once
installed — the repository verifier enforces exactly that. So this holds no path to a sibling and no list of
names. It looks at the directory this Skill is installed in and reports whichever siblings are there, which
is correct in this repository, correct beside one installed analyzer, and correct beside none.

The consequence worth stating: **an analyzer Skill is optional.** Nothing here fails when none is installed,
and `/nostdb` keeps working with the vocabulary it ships itself.

# Only the frontmatter is read

`name` and `description`, and nothing else. Every Skill has both — the verifier requires them — and
`description` is what an agent selects a Skill by, so it is exactly what a caller needs to decide whether an
analyzer fits the project in front of them.

Reading further in, into a sibling's `presets/index` or its schemas, would couple this Skill to another's
internal layout. Those are the sibling's own business, and its `SKILL.md` is the part it publishes.

# Why announcing is a command rather than a convention

`using NAME` prints the line and refuses a name that is not installed. Both halves matter. One format means a
reader sees the same sentence every time rather than whatever each run invented, and a test can pin it.

Refusing is the half that is about honesty: a Skill that announced a vocabulary it did not have would be
claiming a reading nobody performed, and the output would look exactly like the one that did.

Usage:
  analyzers.py                every installed analyzer Skill, with what it reads
  analyzers.py path NAME      where one is installed, so its definition can be read
  analyzers.py using NAME     the line to print before using one

Exit codes: 0 answered, 1 nothing matched, 2 used incorrectly.
"""

from __future__ import annotations

import sys
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent

# The directory this Skill is installed in, whose other entries are the Skills installed beside it.
#
# `skills/nostdb` in this repository, `.agents/skills/nostdb` in a project that installed it, and whatever an
# installer chose anywhere else. Derived rather than configured, because a path in a definition is a path
# that is wrong on the first machine that differs.
INSTALLED_BESIDE = FOLDER.parent

# What an analyzer Skill is called. The prefix is the whole convention: a Skill naming a framework's
# vocabulary is `nostdb-analyzer-<framework>`, and one that is not is not offered here.
PREFIX = "nostdb-analyzer-"


def refuse(message: str, code: int) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def frontmatter(definition: Path) -> dict[str, str]:
    """The top-level scalar fields of a `SKILL.md`'s frontmatter.

    A deliberately small reader: it takes `key: value` at the top level between the opening and closing `---`
    and stops there. `description` is one line by convention and `name` always is, so nothing here needs a
    YAML parser — and taking a dependency to read two fields would be a dependency every install has to have.

    A nested block, such as `metadata:`, is skipped rather than misread: its children are indented, and an
    indented line is not a top-level field.
    """
    try:
        lines = definition.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    found: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        found[key.strip()] = value.strip()
    return found


def installed() -> list[tuple[str, str, Path]]:
    """Every analyzer Skill beside this one, in name order.

    A directory matching the prefix with no readable `SKILL.md` is skipped rather than reported. It is not an
    analyzer a caller can use, and naming it would offer a Skill that cannot be selected.
    """
    found = []
    for folder in sorted(INSTALLED_BESIDE.glob(f"{PREFIX}*")):
        if not folder.is_dir():
            continue
        fields = frontmatter(folder / "SKILL.md")
        name = fields.get("name")
        description = fields.get("description")
        if not name or not description:
            continue
        found.append((name, description, folder))
    return found


def locate(name: str) -> tuple[str, str, Path]:
    """One installed analyzer, by its full name or by the framework alone.

    `springboot` and `nostdb-analyzer-springboot` both find it. The short form is what somebody types and the
    long form is what a document names, and refusing either would be refusing a name that is not ambiguous.
    """
    wanted = name if name.startswith(PREFIX) else f"{PREFIX}{name}"
    for entry in installed():
        if entry[0] == wanted:
            return entry
    refuse(f"no analyzer Skill named {wanted} is installed", 1)
    raise AssertionError("unreachable")


def main(argv: list[str]) -> None:
    action = argv[0] if argv else "list"

    if action == "list":
        found = installed()
        if not found:
            # Not a failure. An analyzer Skill is optional, and `/nostdb` works without one.
            print(
                f"no {PREFIX}* Skill is installed beside this one; "
                "the vocabulary this Skill ships is what is available",
                file=sys.stderr,
            )
            return
        for name, description, folder in found:
            print(name)
            print(f"  {description}")
            print(f"  installed: {folder}")
        return

    if action == "path":
        if len(argv) != 2:
            refuse("usage: analyzers.py path NAME", 2)
        print(locate(argv[1])[2])
        return

    if action == "using":
        if len(argv) != 2:
            refuse("usage: analyzers.py using NAME", 2)
        name = locate(argv[1])[0]
        # One sentence, so a reader sees the same one every time. Present tense and no hedging: by the time
        # this is printed the decision has been made, and "may use" would describe a different act.
        print(f"using {name}, an installed NostDB analyzer Skill, for this project's vocabulary")
        return

    refuse("usage: analyzers.py [list | path NAME | using NAME]", 2)


if __name__ == "__main__":
    main(sys.argv[1:])
