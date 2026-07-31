#!/usr/bin/env python3
"""Prints the action surface, without an Engine.

`/nostdb help` describes this Skill. It used to map to `nostdb help`, which meant asking what the Skill can do
required resolving an Engine first — and with none installed, resolution stops and asks whether to install one.
Asking somebody to install a database to read a help message is the wrong order of operations.

The text is extracted from `SKILL.md` rather than written here. Two copies of one surface drift, and the copy
that drifts is the one nobody reads while editing the other. `SKILL.md` is in this folder, so it is present
after an install.

# Where the section ends

The `## Surface` section, up to the next heading of the same level, whatever it is called.

The terminator was `^## [^S]`, which cannot stop at `## Step 1: resolve the Engine` — the heading that
immediately follows Surface, and one of two beginning with the letter it excludes. So `help` printed the surface
and then Engine resolution and the dispatch table after it: a reader asking what the Skill does got three
sections of instructions addressed to the agent.

Exit codes: 0 printed, 2 `SKILL.md` is not beside this script or declares no Surface section.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFINITION = Path(__file__).resolve().parent.parent / "SKILL.md"
OPENING = "## Surface"


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def surface(text: str) -> list[str]:
    """The lines of the Surface section, without the heading that ends it.

    The search for the end starts *after* the opening heading, so the opening cannot terminate its own section
    and needs no exclusion — which is what the old pattern's `[^S]` was trying to arrange and got wrong.
    """
    lines = text.splitlines()
    try:
        start = lines.index(OPENING)
    except ValueError:
        return []
    for at in range(start + 1, len(lines)):
        if lines[at].startswith("## "):
            return lines[start:at]
    return lines[start:]


def main() -> None:
    if not DEFINITION.is_file():
        fail("SKILL.md is not beside this script")
    section = surface(DEFINITION.read_text(encoding="utf-8"))
    if not section:
        fail("SKILL.md declares no Surface section")
    print("\n".join(section))


if __name__ == "__main__":
    main()
