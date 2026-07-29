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

# Every action that runs anything has the CLI run it. Not an equivalent command, and not a
# reimplementation.
#
# Matched on the resolved command appearing rather than on the line starting with `nostdb`, because
# two mappings begin with a guard that decides whether the project needs configuring first.
#
# `help` is deliberately absent: it runs nothing, because `/nostdb help` describes the Skill and the
# Skill is what knows. An action is not required to be one CLI command or to be named after one — what
# is required is that whatever work happens is the CLI's.
for action in build build-nost sync view; do
  got=$(NOSTDB=ENGINE "$dispatch" "$action" 2>/dev/null || echo "REFUSED")
  case "$got" in
    *ENGINE\ *) echo "ok   $action invokes the CLI" ;;
    *) echo "FAIL $action produced [$got]" >&2; failures=$((failures + 1)) ;;
  esac
done

# The resolved command is substituted everywhere it is needed, not prefixed once.
#
# A prefix cannot work: a project-local resolution is a path, the no-install route is four words, and
# a chained mapping names the command more than once. `build-nost` names it three times.
got=$(NOSTDB="npx --yes --package=nostdb nostdb" "$dispatch" build-nost . 2>/dev/null)
check "every occurrence is substituted, not just the first" \
  "$(printf '%s\n' "$got" | grep -o 'npx --yes --package=nostdb nostdb' | wc -l | tr -d ' ')" "3"

# A bare `/nostdb .` is what `build` serves. It is the whole of it: configure if needed, then analyze
# the tree and write the database.
got=$(NOSTDB=ENGINE "$dispatch" build . 2>/dev/null)
case "$got" in
  *"ENGINE init ."*) echo "ok   /nostdb . configures the project" ;;
  *) echo "FAIL build does not init: [$got]" >&2; failures=$((failures + 1)) ;;
esac
case "$got" in
  *"ENGINE build ."*) echo "ok   /nostdb . analyzes the project" ;;
  *) echo "FAIL build does not build: [$got]" >&2; failures=$((failures + 1)) ;;
esac

# Guarded, because `init` refuses an already-configured project and exits 2. Without the guard
# `/nostdb .` would work once and fail every time after.
case "$got" in
  *"[ -f ./.nostdb/settings.json ] ||"*) echo "ok   init is guarded so a re-run still works" ;;
  *) echo "FAIL init is unguarded: [$got]" >&2; failures=$((failures + 1)) ;;
esac

# `--nost` materializes the canonical document as well.
got=$(NOSTDB=ENGINE "$dispatch" build-nost . 2>/dev/null)
case "$got" in
  *"ENGINE export --nost ."*) echo "ok   --nost materializes the .nost" ;;
  *) echo "FAIL build-nost does not export: [$got]" >&2; failures=$((failures + 1)) ;;
esac

# `/nostdb help` needs no Engine. It used to map to `nostdb help`, so reading a help message required
# resolving one — and with none installed, resolution stops and asks whether to install. Nobody should
# have to install a database to find out what a Skill does.
"$dispatch" help >/dev/null 2>&1 && r=$? || r=$?
check "help is not a command the dispatcher maps" "$r" "1"
got=$("$dispatch" help 2>&1 >/dev/null || true)
case "$got" in
  *help.sh*) echo "ok   and it points at the script that answers it" ;;
  *) echo "FAIL help does not name help.sh: [$got]" >&2; failures=$((failures + 1)) ;;
esac

# The help text comes out of SKILL.md rather than being a second copy. Two copies of one surface drift,
# and the one that drifts is the one nobody reads while editing the other.
surface=$("$skill/scripts/help.sh" 2>/dev/null || echo FAILED)
case "$surface" in
  *"/nostdb ."*) echo "ok   help.sh prints the surface with no Engine" ;;
  *) echo "FAIL help.sh printed [$surface]" >&2; failures=$((failures + 1)) ;;
esac
for expected in "/nostdb query --cypher" "/nostdb view ." "/nostdb plugin add" "/nostdb help"; do
  case "$surface" in
    *"$expected"*) : ;;
    *) echo "FAIL the surface omits $expected" >&2; failures=$((failures + 1)) ;;
  esac
done
echo "ok   and it names every action a caller can ask for"

# Extracted rather than copied, proven by editing the source and seeing the edit come out. A grep for a
# string this test invented would pass just as well against a hard-coded copy, which is what this has to
# rule out.
probe="zzz-extraction-probe-$$"
cp "$skill/SKILL.md" "$skill/SKILL.md.orig"
sed -i.bak "s|^/nostdb help .*|/nostdb help                       $probe|" "$skill/SKILL.md"
rm -f "$skill/SKILL.md.bak"
moved=$("$skill/scripts/help.sh" 2>/dev/null || echo FAILED)
mv "$skill/SKILL.md.orig" "$skill/SKILL.md"
case "$moved" in
  *"$probe"*) echo "ok   the text is read from SKILL.md, not copied into the script" ;;
  *) echo "FAIL help.sh did not follow an edit to SKILL.md" >&2; failures=$((failures + 1)) ;;
esac

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

# Which actions the dispatcher maps is decided by *running* it, not by reading its case labels. `help`
# is a label and maps nothing, so a textual scan counted an action that emits no command — and an
# action is no longer required to emit one, which is exactly why the check cannot be textual any more.
labels=""
for label in $(grep -oE '^  [a-z-]+\)$' "$dispatch" | tr -d ' )'); do
  if NOSTDB=ENGINE "$dispatch" "$label" . >/dev/null 2>&1; then
    labels="$labels$label "
  fi
done
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
