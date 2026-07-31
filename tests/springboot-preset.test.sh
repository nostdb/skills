#!/bin/sh
# The Spring Boot vocabulary, and the four names it may not use.
#
# `tests/presets.test.sh` covers the `nostdb` Skill's presets and is written against that folder. This one
# covers this Skill's, and adds the rules that only apply to a second preset shipped beside a first: it may
# not redeclare a label the other one declares, and it may not declare a schema for a relation the Engine
# itself draws.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
skill="$here/../skills/nostdb-analyzer-springboot"
other="$here/../skills/nostdb"
presets="$skill/scripts/presets.py"
index="$skill/presets/index"
document="$skill/presets/springboot.nost"
definition="$skill/SKILL.md"

failures=0
group=0

# Every group below counts its own failures, so its summary reports the group's result. A bare `echo "ok"`
# after a loop prints beside the FAIL it just emitted, which is how a suite reads as passing while telling
# you it did not.
group_start() { group=0; }
group_end() {
  if [ "$group" -eq 0 ]; then
    echo "ok   $1"
  else
    failures=$((failures + group))
  fi
}

check() {
  if [ "$2" = "$3" ]; then
    echo "ok   $1"
  else
    echo "FAIL $1: expected [$3], got [$2]" >&2
    failures=$((failures + 1))
  fi
}

for required in "$index" "$document" "$definition" "$presets"; do
  [ -e "$required" ] || { echo "FAIL missing $required" >&2; exit 1; }
done

# Every row names a document that is there, because a preset nobody can open is not a preset.
rows=$(grep -v '^[[:space:]]*#' "$index" | grep -v '^[[:space:]]*$')
[ -n "$rows" ] || { echo "FAIL the index declares no preset" >&2; exit 1; }
printf '%s\n' "$rows" | while IFS= read -r row; do
  at=1
  for field in name file covers describes; do
    value=$(printf '%s\n' "$row" | awk -F'|' -v at="$at" '{ gsub(/^ +| +$/, "", $at); print $at }')
    [ -n "$value" ] || { echo "FAIL a row has an empty $field: $row" >&2; exit 1; }
    at=$((at + 1))
  done
  named=$(printf '%s\n' "$row" | awk -F'|' '{ gsub(/^ +| +$/, "", $2); print $2 }')
  [ -f "$skill/presets/$named" ] || {
    echo "FAIL the index names $named, which is not in the folder an installer copies" >&2
    exit 1
  }
done || failures=$((failures + 1))
echo "ok   the index names a document that ships"

# The lookup, in both directions.
check "a preset's document is found by name" "$($presets document springboot)" "presets/springboot.nost"
check "an annotation finds the preset covering it" "$($presets for Scheduled)" "springboot"

# Whole-name matching, on pairs this index actually holds.
#
# `Min` is a prefix of `DecimalMin`, `Valid` of `Validated`, `Value` shares a prefix with `Valid`, and
# `Query` with none of them — a substring match would claim this preset for an annotation nobody wrote a
# schema for, and these pairs are why that is not hypothetical here.
check "a prefix is not a match by itself" "$($presets for DecimalMin)" "springboot"
check "and neither is the longer name's prefix" "$($presets for Min)" "springboot"
$presets for Mi >/dev/null 2>&1 && r=$? || r=$?
check "a partial name matches nothing" "$r" "1"

# Dependency injection is deliberately uncovered: this preset declares no `Bean`, so claiming `@Service`
# would point a model at records that do not exist.
group_start
for uncovered in Component Service Autowired Configuration Bean; do
  $presets for "$uncovered" >/dev/null 2>&1 && r=$? || r=$?
  if [ "$r" != "1" ]; then
    echo "FAIL $uncovered is claimed, and this preset has no vocabulary for it" >&2
    group=$((group + 1))
  fi
done
group_end "dependency injection is not claimed"

# The persistence mappings belong to the other Skill's `jpa` preset. Two presets claiming one annotation
# would make the choice between them arbitrary.
group_start
for theirs in Entity Table Column Id GeneratedValue ManyToOne JoinColumn; do
  $presets for "$theirs" >/dev/null 2>&1 && r=$? || r=$?
  if [ "$r" != "1" ]; then
    echo "FAIL $theirs is claimed here and covered by the jpa preset" >&2
    group=$((group + 1))
  fi
done
group_end "the jpa preset's annotations are left to it"

# Listing needs no Engine, for the reason `help` does not.
case "$($presets list 2>/dev/null || echo FAILED)" in
  *springboot*) echo "ok   listing works with no Engine" ;;
  *) echo "FAIL listing produced nothing" >&2; failures=$((failures + 1)) ;;
esac

# `Schema` is not a label any preset declares. NostDB already has schemas — a preset is made of them.
group_start
if grep -qE '^schema Schema[ (]' "$document"; then
  echo "FAIL the preset declares a label called Schema" >&2
  group=$((group + 1))
fi
group_end "no label called Schema"

# A label a build already writes is not redeclared.
#
# A schema is unowned, so a preset sharing a name with a builtin label is replaced on the next build: the
# preset's version vanishes and the only sign is a warning. Referencing one in an endpoint constraint —
# `schema ACCEPTS(Endpoint -> Request)` — is a different thing and is what this preset does.
group_start
for reserved in File Directory Endpoint Asset Component Function Method Struct Field Module \
    Enum Union Trait TypeAlias Constant Impl; do
  if grep -qE "^schema $reserved[ (]" "$document"; then
    echo "FAIL the preset redeclares the builtin label $reserved" >&2
    group=$((group + 1))
  fi
done
group_end "no builtin label is redeclared"

# A relation the Engine itself draws has no schema here.
#
# `HANDLED_BY` runs from `Endpoint` to `Method` in every build. A schema for it here would constrain the
# Engine's own edges to this preset's shape and raise a violation on each of them.
group_start
for relation in CONTAINS CALLS IMPLEMENTS FOR_TYPE IMPORTS HANDLED_BY DECLARED_BY; do
  if grep -qE "^schema $relation[ (]" "$document"; then
    echo "FAIL the preset declares a schema for the builtin relation $relation" >&2
    group=$((group + 1))
  fi
done
group_end "no builtin relation is given a schema"

# And no label the other Skill's presets declare, read from those documents rather than from a list here.
#
# A list would go stale the first time that Skill added a preset, and the failure would be a label silently
# replaced rather than a check that noticed.
theirs=$(grep -hoE '^schema [A-Za-z_][A-Za-z0-9_]*' "$other"/presets/*.nost | awk '{ print $2 }' | sort -u)
mine=$(grep -hoE '^schema [A-Za-z_][A-Za-z0-9_]*' "$document" | awk '{ print $2 }' | sort -u)
shared=$(printf '%s\n' "$theirs" "$mine" | sort | uniq -d)
group_start
if [ -n "$shared" ]; then
  echo "FAIL these labels are declared by both this preset and the nostdb Skill's:" >&2
  printf '%s\n' "$shared" >&2
  group=$((group + 1))
fi
group_end "no label is shared with the nostdb Skill's presets"

# The five relations that reach a build-written record say where the identifier comes from.
#
# An earlier version of this suite pinned the opposite — that they could not be proposed at all — which was
# wrong: `RETURN e` in JSON format yields the identifier, and one of the five was proposed, applied, and
# queried across the boundary. What must stay true is that the preset says how, so a model does not conclude
# from silence that it cannot.
group_start
for relation in ACCEPTS RETURNS RUNS DECLARES_SETTING ROOTED_AT; do
  if ! awk -v want="schema $relation" '
    $0 ~ "^" want "[ (]" { print block; exit }
    /^\/\// { block = block $0 "\n"; next }
    { block = "" }
  ' "$document" | grep -q "identifier comes from a query"; then
    echo "FAIL $relation does not say where its endpoint's identifier comes from" >&2
    group=$((group + 1))
  fi
done
group_end "every relation reaching a build-written record says how"

# Both limits are stated where a model reads, not only in the preset's comments.
#
# The second is the list-valued properties: `.nost` has list properties and a schema may declare `string[]`,
# which is why `nostdb check` accepts this preset — but a change set's property reader takes a boolean, a
# string, and a number, and refuses an array. A model told to fill `Table.primary_key` would have its whole
# proposal refused for one field.
group_start
for stated in "An edge into a record a build wrote needs its identifier" \
    "--format json" \
    "Do not propose a list-valued property" \
    "Java and Kotlin, both" \
    "primary-constructor properties"; do
  case "$(cat "$definition")" in
    *"$stated"*) ;;
    *)
      echo "FAIL SKILL.md does not say: $stated" >&2
      group=$((group + 1)) ;;
  esac
done
group_end "and the definition states both limits where a model reads"

# And the list-valued fields are still lists, rather than flattened to dodge the limit.
#
# A composite key is a list, and joining one into a comma-separated string would put a format in the graph
# that every later reader has to parse. The field stays a list so it holds one when a change set can carry it.
group_start
for listed in path_variables query_parameters headers primary_key indexes; do
  if ! grep -qE "^  $listed\\?: string\\[\\]" "$document"; then
    echo "FAIL $listed is no longer declared as a list" >&2
    group=$((group + 1))
  fi
done
group_end "the list-valued fields are still lists"

# And the Engine validates the preset, which is the point of it being `.nost`.
#
# This is the only check that would have caught the `@nost 2` the other Skill's preset carried for two
# releases after the language moved to 3. It skipped there because nothing put an Engine on the path; the
# root workspace verifier now does.
if command -v nostdb >/dev/null 2>&1; then
  out=$(nostdb check "$document" 2>&1 || true)
  case "$out" in
    *valid*) echo "ok   the Engine reads the preset" ;;
    *) echo "FAIL the Engine refused the preset: $out" >&2; failures=$((failures + 1)) ;;
  esac
else
  echo "skip no nostdb on the path; the preset was not handed to an Engine"
fi

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "springboot preset: every check passed"
