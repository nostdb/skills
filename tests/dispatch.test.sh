#!/bin/sh
# Ties the action table to the dispatcher, in both directions.
#
# A table row with no mapping fails, and a mapping with no table row fails. A table that
# drifted from the dispatcher would describe a Skill that does not exist, and a dispatcher
# with an undeclared action would be one nobody could budget for.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
skill="$here/../skills/nostdb"
dispatch="$skill/scripts/dispatch.sh"
table="$skill/ACTIONS.md"
definition="$skill/SKILL.md"

failures=0
check() {
  if [ "$2" = "$3" ]; then
    echo "ok   $1"
  else
    echo "FAIL $1: expected [$3], got [$2]" >&2
    failures=$((failures + 1))
  fi
}

# Every AI-free action maps to a command that starts with `nostdb`. Not an equivalent
# command, and not a reimplementation: the same one the CLI offers.
for action in help build build-nost sync view; do
  got=$("$dispatch" "$action" 2>/dev/null || echo "REFUSED")
  case "$got" in
    nostdb\ *) echo "ok   $action invokes the CLI" ;;
    *) echo "FAIL $action produced [$got]" >&2; failures=$((failures + 1)) ;;
  esac
done

got=$("$dispatch" query-cypher 'MATCH (n) RETURN n' 2>/dev/null)
check "a written statement is passed through unchanged" "$got" "nostdb query MATCH (n) RETURN n"

got=$("$dispatch" plugin-add 'https://github.com/o/r' 2>/dev/null)
check "plugin installation goes through the CLI" "$got" "nostdb plugin add https://github.com/o/r"

# An action needing a model is refused specifically, not reported as unknown. Reporting it
# as unknown would suggest a typo when the truth is that it exists and needs something this
# path cannot supply.
"$dispatch" query-natural >/dev/null 2>&1 && r=$? || r=$?
check "a model-requiring action exits 1, not 2" "$r" "1"
"$dispatch" frobnicate >/dev/null 2>&1 && r=$? || r=$?
check "an unknown action exits 2" "$r" "2"

# Three vocabularies, one map.
#
# SKILL.md carries the map, because SKILL.md is the file an agent actually reads. It used to
# live here, in a case statement, which meant the one place the table's vocabulary and the
# dispatcher's met was a test no running agent ever opens: an agent could read the table,
# learn that `/nostdb . --ai=off` exists, and have no way to discover that the action serving
# it is called `build`.
#
# So the map is shipped and this checks it, rather than the reverse. Each row names an action,
# the `/nostdb` invocation it serves, and its declared AI usage.
# Anchored on the third column being a `/nostdb` invocation, not on column count. SKILL.md
# holds more than one table, and an earlier version of this matched the natural-language gate's
# two-column table as well, reading `execute` as an action that served a sentence of prose.
map=$(
  awk -F'|' '
    $2 ~ /^ *`[a-z-]+` *$/ && $3 ~ /^ *`\/nostdb / && $4 ~ /^ *(none|optional|required) *$/ {
      for (field = 2; field <= 4; field++) {
        gsub(/^ +| +$/, "", $field)
        gsub(/`/, "", $field)
      }
      print $2 "\t" $3 "\t" $4
    }
  ' "$definition"
)
[ -n "$map" ] || { echo "FAIL SKILL.md declares no action map" >&2; exit 1; }

# The dispatcher maps exactly the actions SKILL.md declares as runnable without a model.
#
# Stated as a set rather than counted, because counting got it wrong: `build-nost` is the
# AI-free path of an *optional* row, and `optional` means precisely that the action completes
# without a model. So the dispatcher legitimately maps more than the `none` rows, and an
# arithmetic check on prose could not express that.
ai_free=$(printf '%s\n' "$map" | awk -F'\t' '$3 != "required" { printf "%s ", $1 }')
labels=$(grep -oE '^  [a-z-]+\)$' "$dispatch" | tr -d ' )' | tr '\n' ' ')
check "the dispatcher maps exactly the AI-free actions SKILL.md declares" "$labels" "$ai_free"

# And every invocation SKILL.md promises is one the table declares, with the same AI usage.
# A shipped document promising an action the table never declared would be describing a Skill
# that does not exist, which is the failure this file has always existed to prevent.
printf '%s\n' "$map" | while IFS="$(printf '\t')" read -r action serves usage; do
  row=$(grep -F -- "\`$serves\`" "$table" || true)
  if [ -z "$row" ]; then
    echo "FAIL $action serves $serves, which the table does not declare" >&2
    exit 1
  fi
  case "$row" in
    *"| $usage |"*) echo "ok   $action serves $serves, declared $usage" ;;
    *)
      echo "FAIL $action is declared $usage in SKILL.md and otherwise in the table" >&2
      exit 1
      ;;
  esac
done || failures=$((failures + 1))

# A `required` row must not be reachable through this path at all.
for action in query-natural enrich; do
  "$dispatch" "$action" >/dev/null 2>&1 && {
    echo "FAIL $action was dispatched without a model" >&2
    failures=$((failures + 1))
  } || echo "ok   $action is not reachable AI-free"
done

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "dispatch: every check passed"
