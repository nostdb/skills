#!/bin/sh
# The presets, and the boundary they must not cross.
#
# A preset is a vocabulary and a validation target. What this suite pins is that the Skill holds no reader of
# its own: the presets are `.nost` documents, and the Engine is what validates them.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
skill="$here/../skills/nostdb"
presets="$skill/scripts/presets.py"
index="$skill/presets/index"

failures=0
check() {
  if [ "$2" = "$3" ]; then
    echo "ok   $1"
  else
    echo "FAIL $1: expected [$3], got [$2]" >&2
    failures=$((failures + 1))
  fi
}

# Every row names a document that is there, because a preset nobody can open is not a preset.
rows=$(grep -v '^[[:space:]]*#' "$index" | grep -v '^[[:space:]]*$')
[ -n "$rows" ] || { echo "FAIL the index declares no preset" >&2; exit 1; }
printf '%s\n' "$rows" | while IFS= read -r row; do
  name=$(printf '%s\n' "$row" | awk -F'|' '{ gsub(/^ +| +$/, "", $1); print $1 }')
  document=$(printf '%s\n' "$row" | awk -F'|' '{ gsub(/^ +| +$/, "", $2); print $2 }')
  covers=$(printf '%s\n' "$row" | awk -F'|' '{ gsub(/^ +| +$/, "", $3); print $3 }')
  describes=$(printf '%s\n' "$row" | awk -F'|' '{ gsub(/^ +| +$/, "", $4); print $4 }')
  for field in "$name" "$document" "$covers" "$describes"; do
    [ -n "$field" ] || { echo "FAIL a row of the index has an empty field: $row" >&2; exit 1; }
  done
  [ -f "$skill/presets/$document" ] || {
    echo "FAIL $name names $document, which is not in the folder an installer copies" >&2
    exit 1
  }
  echo "ok   $name ships $document"
done || failures=$((failures + 1))

# The lookup, in both directions.
check "a preset's document is found by name" "$($presets document jpa)" "presets/jpa.nost"
check "an annotation finds the preset covering it" "$($presets for Entity)" "jpa"
check "and a whole name is matched, not a substring" "$($presets for ManyToOne)" "jpa"

$presets document nope >/dev/null 2>&1 && r=$? || r=$?
check "an unknown preset exits 1" "$r" "1"
$presets for Nope >/dev/null 2>&1 && r=$? || r=$?
check "an uncovered annotation exits 1" "$r" "1"
$presets frobnicate >/dev/null 2>&1 && r=$? || r=$?
check "an unknown subcommand exits 2" "$r" "2"

# Listing needs no Engine, for the reason `help` does not.
listed=$($presets list 2>/dev/null || echo FAILED)
case "$listed" in
  *jpa*) echo "ok   listing works with no Engine" ;;
  *) echo "FAIL listing produced [$listed]" >&2; failures=$((failures + 1)) ;;
esac

# `Schema` is not a label any preset declares.
#
# NostDB already has schemas — a preset is made of them — so a label called `Schema` would make
# `MATCH (s:Schema)` mean two things at once.
for document in "$skill"/presets/*.nost; do
  if grep -qE '^schema Schema[ (]' "$document"; then
    echo "FAIL $(basename "$document") declares a label called Schema" >&2
    failures=$((failures + 1))
  fi
done
echo "ok   no preset declares a label called Schema"

# The names a build already writes are not redeclared.
#
# A schema is unowned, so a preset sharing a name with a builtin label is replaced on the next build. The
# preset would vanish and the only sign would be a warning.
for reserved in File Directory Endpoint Asset Component Function Method Struct Field Module; do
  for document in "$skill"/presets/*.nost; do
    if grep -qE "^schema $reserved[ (]" "$document"; then
      echo "FAIL $(basename "$document") redeclares the builtin label $reserved" >&2
      failures=$((failures + 1))
    fi
  done
done
echo "ok   no preset redeclares a label a build already writes"

# And the Engine validates every preset, which is the point of them being `.nost`.
if command -v nostdb >/dev/null 2>&1; then
  for document in "$skill"/presets/*.nost; do
    out=$(nostdb check "$document" 2>&1 || true)
    case "$out" in
      *valid*) echo "ok   the Engine reads $(basename "$document")" ;;
      *)
        echo "FAIL the Engine refused $(basename "$document"): $out" >&2
        failures=$((failures + 1)) ;;
    esac
  done
else
  echo "skip no nostdb on the path; the presets were not handed to an Engine"
fi

# A preset an annotation does not select is reported as such, and never as an annotation match.
#
# `project` describes the repository itself, which every project has whether or not it has annotations. The
# index marks that with `*`. Two things have to hold together: `always` finds it, and `for` does *not* — a
# reader that treated `*` as an annotation name would claim this preset for a build that reported a literal
# asterisk, and one that dropped the row would hide the only preset that always applies.
if python3 "$skill/scripts/presets.py" always | grep -qx "project"; then
  echo "ok   the always-applicable preset is reported by name"
else
  echo "FAIL presets.py always does not report project" >&2
  failures=$((failures + 1))
fi

if python3 "$skill/scripts/presets.py" for '*' >/dev/null 2>&1; then
  echo "FAIL presets.py for '*' matched; `*` is a marker, not an annotation name" >&2
  failures=$((failures + 1))
else
  echo "ok   the marker is refused where an annotation belongs"
fi

# And it is still an ordinary preset everywhere else: listed, and resolvable to a document.
for wanted in project jpa; do
  if [ "$(python3 "$skill/scripts/presets.py" document "$wanted")" = "presets/$wanted.nost" ]; then
    echo "ok   $wanted resolves to its document"
  else
    echo "FAIL $wanted does not resolve to presets/$wanted.nost" >&2
    failures=$((failures + 1))
  fi
done

# The project vocabulary names one required field and nothing an analyzer already reports.
#
# `name` required is the whole of what a `Project` record must carry: a record with no name is one nothing can
# refer to. Every other field is optional because an absent value and a guessed one are different claims.
project="$skill/presets/project.nost"
if grep -qE '^  name: string,$' "$project"; then
  echo "ok   the project vocabulary requires a name"
else
  echo "FAIL project.nost does not require name" >&2
  failures=$((failures + 1))
fi

# A preset holds facts nothing else can claim. These are the analyzers', and a second copy owned by `ai`
# would be the same fact twice with no way to tell which a query should trust.
for owned in file_count line_count languages; do
  if grep -qE "^  $owned\??:" "$project"; then
    echo "FAIL project.nost declares $owned, which a build already reports" >&2
    failures=$((failures + 1))
  fi
done
echo "ok   the project vocabulary claims nothing an analyzer reports"

# The nested fields the request asked for are objects rather than flat strings, so a version stays readable
# rather than being buried in text nothing can take back out.
for nested in tech_stack structure; do
  if grep -qE "^  $nested\?: \{$" "$project"; then
    echo "ok   $nested is an object type"
  else
    echo "FAIL $nested is not declared as an object type" >&2
    failures=$((failures + 1))
  fi
done

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "presets: every check passed"
