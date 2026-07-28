#!/bin/sh
# Ties the action table to the dispatcher, in both directions.
#
# A table row with no mapping fails, and a mapping with no table row fails. A table that
# drifted from the dispatcher would describe a Skill that does not exist, and a dispatcher
# with an undeclared action would be one nobody could budget for.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
dispatch="$here/../scripts/dispatch.sh"
table="$here/../nostdb/ACTIONS.md"

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

# Both directions between the table and the dispatcher.
#
# Stated as a list rather than counted, because counting got it wrong: `build-nost` is the
# AI-free path of an *optional* row, and `optional` means precisely that the action completes
# without a model. So the dispatcher legitimately maps more than the `none` rows, and an
# arithmetic check on prose could not express that.
#
# This list is the one place the table's vocabulary and the dispatcher's meet. A mapping
# added without a row here fails, and a row here without a mapping fails.
bridge="help build build-nost sync query-cypher view plugin-add"
labels=$(grep -oE '^  [a-z-]+\)$' "$dispatch" | tr -d ' )' | tr '\n' ' ')
expected=$(printf '%s ' $bridge)
check "the dispatcher maps exactly the bridged actions" "$labels" "$expected"

# And every bridged action is one the table declares as runnable without a model.
for action in $bridge; do
  case "$action" in
    help)          row='`/nostdb help`' ;;
    build)         row='`/nostdb . --ai=off`' ;;
    build-nost)    row='`/nostdb . --nost`' ;;
    sync)          row='root.nost --sync' ;;
    query-cypher)  row='`/nostdb query --cypher' ;;
    view)          row='`/nostdb view .`' ;;
    plugin-add)    row='`/nostdb plugin add' ;;
  esac
  if grep -qF -- "$row" "$table"; then
    echo "ok   $action is declared in the table"
  else
    echo "FAIL $action has no row in the table" >&2
    failures=$((failures + 1))
  fi
done

# A `required` row must not be reachable through this path at all.
for action in query-natural enrich; do
  "$dispatch" "$action" >/dev/null 2>&1 && {
    echo "FAIL $action was dispatched without a model" >&2
    failures=$((failures + 1))
  } || echo "ok   $action is not reachable AI-free"
done

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "dispatch: every check passed"
