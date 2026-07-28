#!/bin/sh
# Decides what happens to a natural-language proposal.
#
# A model produces a proposal: what kind of request it thinks this was, and the openCypher it
# generated. This applies policy to that proposal, and the policy is the part that can be
# tested — a model's output is not reproducible even in principle, but what is done with it
# is entirely deterministic.
#
# Reads a proposal as JSON on standard input. Prints one of:
#
#   execute   a read: show the statement, then run it
#   confirm   a write: show the exact scope, and run nothing until somebody says so
#   clarify   ambiguous: ask, and run nothing
#   refuse    the proposal cannot be acted on at all
#
# Exit codes: 0 execute, 1 confirm, 2 clarify, 3 refuse, 4 the proposal could not be read.
set -eu

confirmed=${1:-unconfirmed}
proposal=$(cat)

field() {
  echo "$proposal" | tr -d '\n' | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -1
}

kind=$(field kind)
cypher=$(field cypher)

[ -n "$kind" ] || { echo "the proposal states no kind" >&2; exit 4; }

if [ "$kind" = "ambiguous" ]; then
  # Asked and not executed, even if a caller passed confirmation. Confirming a request
  # nobody has stated precisely is confirming the Skill's guess at it.
  echo "clarify"
  echo "the request has more than one reading; ask rather than pick one" >&2
  exit 2
fi

[ -n "$cypher" ] || { echo "the proposal states no statement" >&2; exit 4; }

# What the statement *is*, not what the proposal says it is.
#
# This is the whole safety property here. A model that mislabels a DELETE as a read would
# otherwise have it executed with no confirmation, and the label is the one part of a
# proposal that costs nothing to get wrong. So the statement is inspected, and a write clause
# makes it a write however it was announced.
#
# String literals are stripped first: a statement returning the text "DELETE" is a read.
stripped=$(echo "$cypher" | sed "s/'[^']*'//g; s/\"[^\"]*\"//g" | tr '[:lower:]' '[:upper:]')
# The clauses the Engine's query subset treats as writes are CREATE, DELETE, DETACH, MERGE,
# REMOVE, and SET. This list covers all of them — DETACH only ever appears as DETACH DELETE —
# and adds DROP, which the subset does not support at all. Being conservative beyond the
# Engine is the right direction: the cost is a confirmation prompt for a statement that would
# have been refused anyway.
writes=no
for clause in CREATE MERGE DELETE DETACH SET REMOVE DROP; do
  if echo "$stripped" | grep -qE "(^|[^A-Z])$clause([^A-Z]|$)"; then
    writes=yes
    break
  fi
done
# A procedure call can write without naming a clause, and this cannot tell which does.
# Treating every call as a write is the conservative reading, and being asked to confirm a
# read is a smaller cost than a write running unconfirmed.
if echo "$stripped" | grep -qE "(^|[^A-Z])CALL([^A-Z]|$)"; then
  writes=yes
fi

if [ "$writes" = no ]; then
  if [ "$kind" = "write" ]; then
    # The proposal claims a write and the statement does not write. Refused rather than
    # downgraded: the two disagree, and running the statement would mean deciding the
    # model was wrong about its own intent.
    echo "refuse"
    echo "the proposal claims a write and the statement writes nothing" >&2
    exit 3
  fi
  echo "execute"
  echo "a read: show the statement, then run it" >&2
  exit 0
fi

if [ "$confirmed" != "confirmed" ]; then
  echo "confirm"
  echo "a write: show the exact scope and run nothing until somebody says so" >&2
  exit 1
fi

echo "execute"
echo "a write, confirmed" >&2
exit 0
