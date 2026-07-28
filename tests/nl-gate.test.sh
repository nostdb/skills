#!/bin/sh
# Proves what happens to a natural-language proposal.
#
# No model is called. What a model produces cannot be pinned by a fixture, but what is done
# with what it produces is entirely deterministic, and that is the part with the safety
# properties in it.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
gate="$here/../skills/nostdb/scripts/nl-gate.sh"

failures=0
expect() {
  label=$1; kind=$2; cypher=$3; confirmed=$4; want=$5
  got=$(printf '{"kind":"%s","cypher":"%s"}' "$kind" "$cypher" \
    | "$gate" "$confirmed" 2>/dev/null || true)
  if [ "$got" = "$want" ]; then
    echo "ok   $label"
  else
    echo "FAIL $label: expected [$want], got [$got]" >&2
    failures=$((failures + 1))
  fi
}

expect "a read runs" \
  read "MATCH (n:Function) RETURN n.name" unconfirmed execute

expect "a write waits" \
  write "CREATE (n:Note {text: 'x'})" unconfirmed confirm

expect "a confirmed write runs" \
  write "CREATE (n:Note {text: 'x'})" confirmed execute

# The property this file exists for. The label is the one part of a proposal that costs
# nothing to get wrong, so the statement is what decides.
expect "a write labelled as a read still waits" \
  read "MATCH (n) DETACH DELETE n" unconfirmed confirm
expect "a SET labelled as a read still waits" \
  read "MATCH (n) SET n.x = 1" unconfirmed confirm
expect "a MERGE labelled as a read still waits" \
  read "MERGE (n:Note)" unconfirmed confirm

# A procedure can write without naming a clause, and this cannot tell which does. Being
# asked to confirm a read is a smaller cost than a write running unconfirmed.
expect "a procedure call is treated as a write" \
  read "CALL nostdb.something()" unconfirmed confirm

# A statement returning the text "DELETE" is a read. Stripping literals first is what keeps
# the conservative rule above from being unusable.
expect "a literal containing a keyword is still a read" \
  read "MATCH (n) WHERE n.name = 'DELETE' RETURN n" unconfirmed execute
expect "a double-quoted keyword is still a read" \
  read 'MATCH (n) WHERE n.op = \"DELETE\" RETURN n' unconfirmed execute

# Ambiguity is not resolved by confirmation. Confirming a request nobody has stated
# precisely is confirming the Skill's guess at it.
expect "an ambiguous request asks" \
  ambiguous "MATCH (n) RETURN n" unconfirmed clarify
expect "an ambiguous request asks even when confirmed" \
  ambiguous "MATCH (n) DETACH DELETE n" confirmed clarify

# A proposal that contradicts itself is refused rather than downgraded: running the
# statement would mean deciding the model was wrong about its own intent.
expect "a write claim with a read statement is refused" \
  write "MATCH (n) RETURN n" confirmed refuse

# A proposal it cannot read grants nothing.
for bad in '{}' '{"kind":"read"}' 'not json'; do
  got=$(printf '%s' "$bad" | "$gate" confirmed 2>/dev/null || true)
  if [ -z "$got" ]; then
    echo "ok   an unreadable proposal grants nothing"
  else
    echo "FAIL an unreadable proposal produced [$got]" >&2
    failures=$((failures + 1))
  fi
done

# Every clause the Engine's own query subset treats as a write is one this gate catches.
# The two lists are in different repositories and cannot import each other, so this is what
# keeps them from drifting: a clause added to the Engine and not here would let a write run
# unconfirmed, which is the one failure this file exists to prevent.
for clause in "CREATE (n)" "MATCH (n) DELETE n" "MATCH (n) DETACH DELETE n" \
              "MERGE (n:X)" "MATCH (n) REMOVE n.x" "MATCH (n) SET n.x = 1"; do
  got=$(printf '{"kind":"read","cypher":"%s"}' "$clause" | "$gate" unconfirmed 2>/dev/null || true)
  if [ "$got" = "confirm" ]; then
    echo "ok   an Engine write clause is caught: $clause"
  else
    echo "FAIL [$clause] produced [$got], not confirm" >&2
    failures=$((failures + 1))
  fi
done

# Nothing here ever prints `execute` for an unconfirmed write, whatever the input.
for statement in "CREATE (n)" "MATCH (n) DELETE n" "MATCH (n) REMOVE n.x" "DROP INDEX x"; do
  got=$(printf '{"kind":"read","cypher":"%s"}' "$statement" | "$gate" unconfirmed 2>/dev/null || true)
  if [ "$got" = "execute" ]; then
    echo "FAIL [$statement] executed unconfirmed" >&2
    failures=$((failures + 1))
  else
    echo "ok   [$statement] did not execute unconfirmed"
  fi
done

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "natural language: every check passed"
