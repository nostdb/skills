#!/bin/sh
# The presets this Skill ships, and which one covers an annotation the Engine did not read.
#
# Answered from this Skill's own files and without an Engine: a preset is part of the Skill, and asking
# somebody to install a database to find out which presets exist is the wrong order of operations.
#
# This is this Skill's own copy rather than a reference to the one the `nostdb` Skill ships, and it has to be.
# An installer copies a skill folder, so anything a definition reaches outside its own folder is absent once
# installed — the repository verifier enforces that, and a shared script would be a Skill that worked here and
# failed everywhere else.
#
# # What a preset is, and what it is not
#
# A preset is a **vocabulary** — the names a proposal uses once something else has read the source — and a
# **validation target**, because it is a `.nost` document the Engine checks like any other. It is not an
# analyzer: nothing here reads `@Scheduled`, and nothing here may derive a fact from one.
#
# That line is the whole boundary. Deriving facts from a preset without a model would make this Skill a second
# analyzer, reading annotations the Engine's own analyzers do not read, which is exactly what the root
# contract's rule about an AI-free action having the CLI do the work prevents.
#
# # What this cannot answer, and what does
#
# Only annotations. The preset also gives names to what a build file and a settings document declare, and no
# build reports an "uninterpreted config file" — a settings document is a `File` the scan recorded like any
# other. Finding those is a query, which the Engine runs; `SKILL.md` carries it.
#
# Usage:
#   presets.sh                 every preset, with what it covers
#   presets.sh document NAME   the path to one preset's `.nost`, for the Engine to check
#   presets.sh for NAME        which preset covers an annotation name, if any
#
# Exit codes: 0 answered, 1 nothing matched, 2 used incorrectly.
set -eu
cd "$(dirname "$0")/.."

index=presets/index
[ -f "$index" ] || { echo "presets/index is not beside this script" >&2; exit 2; }

# Every row, comments and blank lines dropped. One place, so no caller re-derives the format.
rows() {
  grep -v '^[[:space:]]*#' "$index" | grep -v '^[[:space:]]*$'
}

field() {
  printf '%s\n' "$2" | awk -F'|' -v at="$1" '{ gsub(/^ +| +$/, "", $at); print $at }'
}

case "${1:-list}" in
  list)
    rows | while IFS= read -r row; do
      name=$(field 1 "$row")
      printf '%s\n' "$name"
      printf '  %s\n' "$(field 4 "$row")"
      printf '  covers: %s\n' "$(field 3 "$row")"
      printf '  schema: presets/%s\n' "$(field 2 "$row")"
    done
    ;;
  document)
    [ "$#" -eq 2 ] || { echo "usage: presets.sh document NAME" >&2; exit 2; }
    # Trimmed into a variable rather than in place: assigning to `$1` makes awk rebuild `$0` with its output
    # separator, so the `|` this format is made of would be gone by the time the row was printed.
    row=$(rows | awk -F'|' -v want="$2" '
      { name = $1; gsub(/^ +| +$/, "", name); if (name == want) print }
    ')
    [ -n "$row" ] || { echo "no preset named $2" >&2; exit 1; }
    printf 'presets/%s\n' "$(field 2 "$row")"
    ;;
  for)
    # Which preset covers an annotation the Engine reported uninterpreted.
    #
    # Matched on the whole name between commas, so `Min` does not match `DecimalMin` and `Value` does not
    # match a preset covering `Valid`. A substring match would claim a preset for an annotation nobody wrote a
    # schema for — and this index holds several pairs where one name is a prefix of another, so the difference
    # is not hypothetical.
    [ "$#" -eq 2 ] || { echo "usage: presets.sh for ANNOTATION" >&2; exit 2; }
    found=$(rows | awk -F'|' -v want="$2" '
      {
        name = $1; gsub(/^ +| +$/, "", name)
        covers = $3; gsub(/^ +| +$/, "", covers)
        count = split(covers, held, ",")
        for (at = 1; at <= count; at++) {
          gsub(/^ +| +$/, "", held[at])
          if (held[at] == want) { print name; next }
        }
      }
    ')
    [ -n "$found" ] || { echo "no preset covers $2" >&2; exit 1; }
    printf '%s\n' "$found"
    ;;
  *)
    echo "usage: presets.sh [list | document NAME | for ANNOTATION]" >&2
    exit 2
    ;;
esac
