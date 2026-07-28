#!/bin/sh
# Maps an AI-free Skill action to the nostdb command it invokes, and prints it.
#
# This exists so there is exactly one answer to "what does this action do". The Skill is an
# extension of the CLI, not a second engine: an AI-free action must call the same Core
# command the command surface calls, not an equivalent one. Two implementations of one
# action is two answers to one question, and which a user gets would depend on which surface
# they happened to reach for.
#
# Printing the command rather than running it is deliberate. It makes the mapping testable
# without an Engine, and it means a caller can show a user exactly what will run before
# anything does — which is what a natural-language write is separately required to do.
#
# Exit codes: 0 mapped, 1 the action needs a model and has no AI-free mapping, 2 unknown.
set -eu

[ "$#" -ge 1 ] || { echo "usage: dispatch.sh <action> [arguments...]" >&2; exit 2; }
action=$1
shift

# Every row here corresponds to a `none` row in nostdb/ACTIONS.md, and the test asserts that
# correspondence in both directions: a table row with no mapping fails, and a mapping with no
# table row fails. A table that drifted from the dispatcher would describe a Skill that does
# not exist.
case "$action" in
  help)
    echo "nostdb help"
    ;;
  build)
    # `/nostdb .` with enrichment refused. The build itself is AI-free and always was:
    # structural analysis of supported source spends no external tokens.
    echo "nostdb build ${1:-.}"
    ;;
  build-nost)
    echo "nostdb build ${1:-.} && nostdb export --nost ${1:-.}"
    ;;
  sync)
    echo "nostdb sync ${1:-.}"
    ;;
  query-cypher)
    [ "$#" -ge 1 ] || { echo "query-cypher needs a statement" >&2; exit 2; }
    echo "nostdb query $1"
    ;;
  view)
    echo "nostdb view ${1:-.}"
    ;;
  plugin-add)
    [ "$#" -ge 1 ] || { echo "plugin-add needs a source" >&2; exit 2; }
    echo "nostdb plugin add $1"
    ;;
  query-natural|enrich)
    # Named so the refusal is specific. Reporting these as unknown would suggest a typo,
    # when the truth is that they exist and need something this path cannot supply.
    echo "$action requires a model and has no AI-free mapping" >&2
    exit 1
    ;;
  *)
    echo "unknown action: $action" >&2
    exit 2
    ;;
esac
