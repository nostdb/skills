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

# The `## Surface` section, up to the next heading of the same level. `sed` rather than awk for no
# reason beyond it being the shorter expression of "between these two markers".
surface=$(sed -n '/^## Surface$/,/^## [^S]/p' SKILL.md | sed '$d')
[ -n "$surface" ] || { echo "SKILL.md declares no Surface section" >&2; exit 2; }

printf '%s\n' "$surface"
