#!/bin/sh
# Prints the action surface, without an Engine.
#
# `/nostdb help` describes this Skill. It used to map to `nostdb help`, which meant asking what the
# Skill can do required resolving an Engine first — and with none installed, resolution stops and asks
# whether to install one. Asking somebody to install a database to read a help message is the wrong
# order of operations.
#
# The text is extracted from SKILL.md rather than written here. Two copies of one surface drift, and
# the copy that drifts is the one nobody reads while editing the other. SKILL.md is in this folder, so
# it is present after an install.
set -eu
cd "$(dirname "$0")/.."

[ -f SKILL.md ] || { echo "SKILL.md is not beside this script" >&2; exit 2; }

# The `## Surface` section, up to the next heading of the same level, whatever it is called.
#
# The terminator was `^## [^S]`, which cannot stop at `## Step 1: resolve the Engine` — the heading
# that immediately follows Surface, and one of two beginning with the letter it excludes. So `help`
# printed the surface and then Engine resolution and the dispatch table after it: a reader asking
# what the Skill does got three sections of instructions addressed to the agent.
#
# A range end is matched from the line after the start, so a bare `/^## /` cannot re-match the
# opening heading and needs no exclusion. `sed '$d'` drops the terminating heading.
surface=$(sed -n '/^## Surface$/,/^## /p' SKILL.md | sed '$d')
[ -n "$surface" ] || { echo "SKILL.md declares no Surface section" >&2; exit 2; }

printf '%s\n' "$surface"
