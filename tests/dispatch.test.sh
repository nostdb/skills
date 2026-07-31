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
for action in build export sync summary view; do
  got=$(NOSTDB=ENGINE "$dispatch" "$action" 2>/dev/null || echo "REFUSED")
  case "$got" in
    *ENGINE\ *) echo "ok   $action invokes the CLI" ;;
    *) echo "FAIL $action produced [$got]" >&2; failures=$((failures + 1)) ;;
  esac
done

# The resolved command is substituted everywhere it is needed, not prefixed once.
#
# A prefix cannot work: a project-local resolution is a path, the no-install route is four words, and
# a chained mapping names the command more than once. `summary` names it five times.
#
# It used to be `build-nost`, which chained three. That action is now `export` and emits one command, so a
# check anchored on it would have kept passing while testing nothing about substitution.
got=$(NOSTDB="npx --yes --package=nostdb nostdb" "$dispatch" summary . 2>/dev/null)
check "every occurrence is substituted, not just the first" \
  "$(printf '%s\n' "$got" | grep -o 'npx --yes --package=nostdb nostdb' | wc -l | tr -d ' ')" "5"

# A bare `/nostdb .` is what `build` serves. It is the whole of it: configure if needed, then analyze
# the tree and write the database.
got=$(NOSTDB=ENGINE "$dispatch" build . 2>/dev/null)
case "$got" in
  *"ENGINE init ."*) echo "ok   /nostdb . configures the project" ;;
  *) echo "FAIL build does not init: [$got]" >&2; failures=$((failures + 1)) ;;
esac
# `--project .` rather than a bare `.`: release 0.1.0 refuses a positional path to `build`, a later build
# accepts one, and both report the same version data. `--project` is what every version accepts.
case "$got" in
  *"ENGINE build --project ."*) echo "ok   /nostdb . analyzes the project" ;;
  *) echo "FAIL build does not build: [$got]" >&2; failures=$((failures + 1)) ;;
esac

# Guarded, because `init` refuses an already-configured project and exits 2. Without the guard
# `/nostdb .` would work once and fail every time after.
case "$got" in
  *"[ -f ./.nostdb/settings.json ] ||"*) echo "ok   init is guarded so a re-run still works" ;;
  *) echo "FAIL init is unguarded: [$got]" >&2; failures=$((failures + 1)) ;;
esac

# `/nostdb export .` writes the canonical document, and builds nothing.
#
# The surface says `export` and the command says `--nost`, which is not a mismatch: `nost` is the surface's
# default and the flag is spelled at the boundary, because the CLI requires it so a later representation
# cannot silently change what a bare `export` means. So this asserts the flag is present, and the next check
# asserts nothing else is.
got=$(NOSTDB=ENGINE "$dispatch" export . 2>/dev/null)
check "export emits exactly the Engine's export, with the representation spelled" \
  "$got" "ENGINE export --nost ."

# No build and no guard. It used to emit `build && export` behind a flag on `/nostdb .`, so writing the
# document from an already-built database re-analyzed the whole tree — and initializing a project as a side
# effect of asking to read one out is not something anybody asked for.
case "$got" in
  *build* | *init*) echo "FAIL export builds or initializes: [$got]" >&2; failures=$((failures + 1)) ;;
  *) echo "ok   export neither builds nor initializes" ;;
esac

# `/nostdb convert` converts two files, in whichever direction the extensions name.
#
# Asserted in both directions, because the direction is the Engine's to decide from the extensions and a
# dispatcher that reordered or dropped an operand would still look right in one of them.
got=$(NOSTDB=ENGINE "$dispatch" convert a.nost b.nostdb 2>/dev/null)
check "convert emits the input and the output, in order" "$got" "ENGINE convert a.nost b.nostdb"
got=$(NOSTDB=ENGINE "$dispatch" convert x.nostdb y.nost 2>/dev/null)
check "and the other direction is the same command" "$got" "ENGINE convert x.nostdb y.nost"

# Both operands are required. Defaulting either would invent a path nobody named, and the one it would
# invent is an output — a command that writes somewhere nobody asked for is worse than one that refuses.
"$dispatch" convert only.nost >/dev/null 2>&1 && r=$? || r=$?
check "convert with one operand is refused" "$r" "2"

# `sync` takes the **project**, not either representation. The surface used to show
# `/nostdb .nostdb/root.nost --sync`, which names a file — passing that through would hand `sync` a file
# where it expects the project containing it.
got=$(NOSTDB=ENGINE "$dispatch" sync . 2>/dev/null)
check "sync names a project" "$got" "ENGINE sync ."
case "$got" in
  *root.nost*) echo "FAIL sync was given a representation rather than a project: [$got]" >&2
    failures=$((failures + 1)) ;;
  *) echo "ok   and not a representation" ;;
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
for expected in "/nostdb query --cypher" "/nostdb view ." "/nostdb plugin add" "/nostdb summary" "/nostdb help"; do
  case "$surface" in
    *"$expected"*) : ;;
    *) echo "FAIL the surface omits $expected" >&2; failures=$((failures + 1)) ;;
  esac
done
echo "ok   and it names every action a caller can ask for"

# And every value an option accepts, not just the ones an invocation line happens to show.
#
# `--scan=default` was written in prose below the fence and appeared in no help output a reader would scan,
# because the invocation lines show `analyzer` and `ai` and neither says they are two of three. A value nobody
# can see is not documented, so each one is pinned here by name.
for expected in "--scan=default|ai" "--cypher '<statement>'"; do
  case "$surface" in
    *"$expected"*) : ;;
    *) echo "FAIL the surface omits what $expected accepts" >&2; failures=$((failures + 1)) ;;
  esac
done
echo "ok   and says what every option accepts"

# And names nothing the dispatcher does not serve. `--format` is the live case: it is the reserved spelling for
# a second export representation, the Engine has one, and a help screen naming a flag that does nothing
# describes a Skill that does not exist.
#
# The whole surface is checked rather than the options block, because it does not matter where the name
# appears. This caught the sentence that explained the reservation — correct as rationale, and reaching a
# reader who asked what the Skill can do, since `help` extracts the entire section.
case "$surface" in
  *"--format"*)
    echo "FAIL the surface names --format, which nothing serves" >&2
    failures=$((failures + 1)) ;;
  *) echo "ok   and names no option the dispatcher does not serve" ;;
esac

# And it stops at the surface.
#
# Nothing checked where the extraction *ended*, only that it contained the right lines, so a
# terminator of `^## [^S]` went unnoticed: it cannot stop at `## Step 1`, the heading that follows
# Surface, and `help` printed Engine resolution and the dispatch table as well. Somebody asking what
# the Skill does got the instructions written for the agent.
for internal in "## Step 1" "## Step 2" "resolve-engine.sh" "## Natural language"; do
  case "$surface" in
    *"$internal"*)
      echo "FAIL the surface runs past its section into [$internal]" >&2
      failures=$((failures + 1)) ;;
    *) : ;;
  esac
done
echo "ok   and stops there, rather than spilling into the agent's instructions"

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

# `/nostdb summary` asks the Engine every number it reports.
#
# Pinned command by command, because the failure this guards against is not a mapping that drifts —
# it is a Skill that stops asking. Counting nodes in a shell is a few lines that would pass every
# other check in this file while being a second implementation of the question.
got=$(NOSTDB=ENGINE "$dispatch" summary . 2>/dev/null)
for expected in \
  "ENGINE query 'CALL nostdb.build_status()' --project ." \
  "ENGINE query 'MATCH (n) RETURN nostdb.link_alias(n) AS alias, count(n) AS total ORDER BY total DESC' --project ." \
  "ENGINE query 'MATCH (n) RETURN labels(n) AS labels, count(n) AS total ORDER BY total DESC, labels' --project ." \
  "ENGINE query 'MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS total ORDER BY total DESC, type' --project ." \
  "ENGINE check ./.nostdb/root.nostdb"
do
  case "$got" in
    *"$expected"*) echo "ok   summary asks the Engine: ${expected#ENGINE }" ;;
    *) echo "FAIL summary omits [$expected]: [$got]" >&2; failures=$((failures + 1)) ;;
  esac
done

# The totals and the kinds are separate questions, and the declared count is a third.
#
# A build declares a schema for every label its analyzers can write, so fourteen declared schemas
# over three kinds of node is the normal state. An action reporting the declared count as the kinds
# present would describe a graph nobody has, and every check above would still pass — so the reads
# that keep them apart are required to all be there. Two aggregating queries, and `check`.
check "the kinds present are counted from the graph, not inferred from the schema count" \
  "$(printf '%s\n' "$got" | grep -o 'count(' | wc -l | tr -d ' ')" "3"
case "$got" in
  *check*) echo "ok   and the declared schema count comes from the container" ;;
  *) echo "FAIL summary never asks for the declared schemas" >&2; failures=$((failures + 1)) ;;
esac

# A linked project's report has to reconcile. `build_status` answers from the root and a read sees
# the union, so one link makes the totals say 5 nodes while the breakdowns account for 11 — and
# without the per-source count there is nothing in the output that explains the gap. Dropping this
# read leaves a report that contradicts itself and every other check here still passing.
case "$got" in
  *"nostdb.link_alias(n) AS alias"*)
    echo "ok   and the report says which records came from where" ;;
  *) echo "FAIL summary cannot reconcile root totals with union breakdowns: [$got]" >&2
     failures=$((failures + 1)) ;;
esac

# Grouped, never filtered. The subset has no `IS NULL`, so a `WHERE` scoping to the root is a
# semantic error the Engine refuses rather than a narrower query.
case "$got" in
  *"IS NULL"*)
    echo "FAIL summary filters on IS NULL, which the subset refuses: [$got]" >&2
    failures=$((failures + 1)) ;;
  *) echo "ok   and separates the root by grouping, not by a filter the subset lacks" ;;
esac

# `check` runs last, because it is the one call that exits non-zero on a sound report: 3 when the
# container holds an error diagnostic. Earlier in an `&&` chain it would suppress the counts that
# were actually asked for.
case "$got" in
  *"check ./.nostdb/root.nostdb") echo "ok   the call that can fail runs last" ;;
  *) echo "FAIL check is not last, so a failure would hide the summary: [$got]" >&2
     failures=$((failures + 1)) ;;
esac

# Nothing in a summary writes. `export` would materialize `.nost` as a side effect of a read, and
# `build` would commit a generation; a report that changed the thing it reported on is not a report.
case "$got" in
  *export*|*"build "*|*init*|*sync*|*apply*)
    echo "FAIL summary emits a writing command: [$got]" >&2; failures=$((failures + 1)) ;;
  *) echo "ok   summary writes nothing" ;;
esac

# Both spellings of one database. Somebody asks about a `.nostdb` folder as readily as a project,
# usually with the trailing slash a shell completed, and `check` takes the container file — so the
# folder must not become `.nostdb/.nostdb/root.nostdb`.
for named in 'proj/.nostdb' 'proj/.nostdb/' '.nostdb' '.nostdb/'; do
  got=$(NOSTDB=ENGINE "$dispatch" summary "$named" 2>/dev/null)
  want="ENGINE check ${named%/}/root.nostdb"
  case "$got" in
    *"$want"*) echo "ok   $named names the container directly" ;;
    *) echo "FAIL $named resolved wrong; wanted [$want] in [$got]" >&2
       failures=$((failures + 1)) ;;
  esac
done
got=$(NOSTDB=ENGINE "$dispatch" summary proj 2>/dev/null)
case "$got" in
  *"ENGINE check proj/.nostdb/root.nostdb"*) echo "ok   and a project gets its .nostdb appended" ;;
  *) echo "FAIL a project path did not resolve to its container: [$got]" >&2
     failures=$((failures + 1)) ;;
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
# learn that `/nostdb . --scan=ai` exists, and have no way to discover that the action serving
# it is called `enrich`.
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
# Stated as a set rather than counted, because counting got it wrong: `build` is the AI-free
# path of an *optional* row, and `optional` means precisely that the action completes without
# a model. So the dispatcher legitimately maps more than the `none` rows, and an arithmetic
# check on prose could not express that.
ai_free=$(printf '%s\n' "$map" | awk -F'\t' '$3 != "required" { printf "%s ", $1 }')

# Which actions the dispatcher maps is decided by *running* it, not by reading its case labels. `help`
# is a label and maps nothing, so a textual scan counted an action that emits no command — and an
# action is no longer required to emit one, which is exactly why the check cannot be textual any more.
labels=""
for label in $(grep -oE '^  [a-z-]+\)$' "$dispatch" | tr -d ' )'); do
  # Two arguments, not one. `convert` takes an input and an output and refuses with fewer, so probing with
  # a single path reported it as an action the dispatcher does not map — while it does. Every other action
  # reads only what it needs, so a spare argument changes nothing for them.
  if NOSTDB=ENGINE "$dispatch" "$label" . . >/dev/null 2>&1; then
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

# Every emitted command is one a real Engine accepts.
#
# The suite used to pin only the *string* the dispatcher printed, and never asked whether anything would
# run it. Pinning a string proves the mapping did not drift; it does not prove the mapping works.
#
# Its reach is exactly the Engine on this path, and that is worth being clear about: it would **not**
# have caught the bug that prompted it. `build <path>` is refused by release 0.1.0 and accepted by a
# later build, and both report byte-identical `--version --json` — so run against a fixed Engine this
# passes, and Engine resolution cannot tell the two apart either. The check above, which requires
# `--project` by name, is what pins that decision; this one catches a command no Engine would take.
if command -v nostdb >/dev/null 2>&1; then
  work=$(mktemp -d)
  # Configured first, so the guard is exercised in the state a second run is in.
  nostdb init "$work" >/dev/null 2>&1 || true
  for action in build export sync summary view; do
    emitted=$(NOSTDB=nostdb "$dispatch" "$action" "$work" 2>/dev/null)
    out=$(sh -c "$emitted" 2>&1 || true)
    case "$out" in
      *"does not take"* | *"unknown option"* | *"needs a"* | *"Run \`nostdb help\`"*)
        echo "FAIL $action emits a command the Engine refuses: $out" >&2
        failures=$((failures + 1)) ;;
      *) echo "ok   $action emits a command the Engine accepts" ;;
    esac
  done
  # And a statement, which takes its argument a different way again.
  emitted=$(NOSTDB=nostdb "$dispatch" query-cypher 'MATCH (n) RETURN n' 2>/dev/null)
  out=$(cd "$work" && sh -c "$emitted" 2>&1 || true)
  case "$out" in
    *"does not take"* | *"unknown option"*)
      echo "FAIL query-cypher emits a command the Engine refuses: $out" >&2
      failures=$((failures + 1)) ;;
    *) echo "ok   query-cypher emits a command the Engine accepts" ;;
  esac
  rm -rf "$work"
else
  echo "skip no nostdb on the path; the emitted commands were not run"
fi

# `init` is left out when the project is already configured, and present when it is not. A guard that is
# correct and *looks* wrong gets reported as a bug, which is what happened.
configured=$(mktemp -d)
mkdir -p "$configured/.nostdb" && : > "$configured/.nostdb/settings.json"
got=$(NOSTDB=ENGINE "$dispatch" build "$configured" 2>/dev/null)
case "$got" in
  *init*) echo "FAIL a configured project is still told to init: $got" >&2; failures=$((failures + 1)) ;;
  *) echo "ok   a configured project is not told to init" ;;
esac
rm -rf "$configured"

absent=$(mktemp -d) && rmdir "$absent"
got=$(NOSTDB=ENGINE "$dispatch" build "$absent" 2>/dev/null)
case "$got" in
  *"|| ENGINE init"*) echo "ok   an unconfigured one is, and the guard is still there" ;;
  *) echo "FAIL an unconfigured project is not told to init: $got" >&2; failures=$((failures + 1)) ;;
esac


# The Skill's own prose is checked too, because that is where this escaped.
#
# `SKILL.md` documented `nostdb plan --format json .` for the enrichment step. The dispatcher never
# emits it, so every check above passed while the one command a reader would copy was refused by
# release 0.1.0 and — because an option came first — by a later build as well.
#
# The rule is the one already decided for `build`: a documented invocation names its project with
# `--project`, which every version accepts in either position. A bare `.` depends both on the
# Engine's version and on where in the line it sits.
#
# Lines beginning with `nostdb` only, so the Skill's own `/nostdb .` surface is not mistaken for a
# CLI invocation. It is the Skill's spelling and takes a bare path by design.
#
# The rule reaches only the commands that have the option. `--project` exists for `build`, `plan`,
# `query`, `link`, and `apply`; `check`, `init`, `convert`, `export`, `catalog`, `sync`, and `view`
# take a positional target and nothing else. Demanding the option of those would document a flag the
# parser refuses — the same failure this rule exists to prevent, with the sign flipped — and it fired
# exactly that way on `summary`, which documents `nostdb check ./.nostdb/root.nostdb` because that is
# the only spelling `check` has.
positional_only='init check convert export catalog sync view'
documented=0
for document in "$skill"/*.md; do
  while IFS= read -r text; do
    [ -n "$text" ] || continue
    documented=$((documented + 1))
    case " $text " in
      *" --project "*) continue ;;
    esac
    # The subcommand, which is what decides whether the option was available to be named.
    case " $positional_only " in
      *" $(printf '%s\n' "$text" | awk '{print $2}') "*) continue ;;
    esac
    case " $text " in
      *" . "* | *" ."*)
        echo "FAIL $(basename "$document") documents a bare positional path: $text" >&2
        failures=$((failures + 1)) ;;
    esac
  done <<EOF
$(grep -hE '^[[:space:]]*nostdb ' "$document" || true)
EOF
done

# And the exemption list is checked against the Engine rather than trusted, because a command that
# gained `--project` would silently leave this rule unenforced for it.
if command -v nostdb >/dev/null 2>&1; then
  for command in $positional_only; do
    if nostdb help "$command" 2>/dev/null | grep -q -- '--project'; then
      echo "FAIL $command is exempted as positional-only but takes --project" >&2
      failures=$((failures + 1))
    fi
  done
  echo "ok   every exempted command really is positional-only"
fi
check "a documented invocation was found to check" "$([ "$documented" -gt 0 ] && echo yes)" "yes"
[ "$failures" -eq 0 ] && echo "ok   every documented invocation names its project with --project"

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "dispatch: every check passed"
