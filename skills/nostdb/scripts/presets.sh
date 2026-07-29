#!/bin/sh
# The presets this Skill ships, and which one covers an annotation the Engine did not read.
#
# Answered from this Skill's own files and without an Engine, for the reason `help.sh` is: a preset is part
# of the Skill, and asking somebody to install a database to find out which presets exist is the wrong order
# of operations.
#
# # What a preset is, and what it is not
#
# A preset is a **vocabulary** — the names a proposal uses once something else has read the source — and a
# **validation target**, because it is a `.nost` document the Engine checks like any other. It is not an
# analyzer: nothing here reads `@Entity`, and nothing here may derive a fact from one.
#
# That line is the whole boundary. Deriving facts from a preset without a model would make this a second
# analyzer, reading annotations the Engine's own analyzers do not read, which is exactly what the root
# contract's rule about an AI-free action having the CLI do the work prevents.
#
# # Why a preset is needed at all
#
# `nostdb-spec/docs/NOST_LANGUAGE.md` accepts a consequence rather than solving it: a record may name a
# schema that was never declared, so a misspelled label is indistinguishable from an intentional bare one and
# "no syntax can tell the two apart while schemas remain optional". Fixing the vocabulary on the producing
# side is the only place the two *can* be told apart.
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
    # Matched on the whole name between commas, so `Id` does not match `GeneratedValue` and `Table` does not
    # match a preset covering `JoinTable`. A substring match would claim a preset for an annotation nobody
    # wrote a schema for.
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
