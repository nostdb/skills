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
# # The command is substituted, not prefixed
#
# `NOSTDB` holds the command `resolve-engine.sh` printed, and defaults to `nostdb`. What is printed
# here is therefore runnable as it stands.
#
# It used to print the literal word `nostdb` and the definition said to run that "prefixed by the
# resolved command". That does not compose. A project-local resolution gives
# `./node_modules/.bin/nostdb`, so prefixing produces `./node_modules/.bin/nostdb nostdb build .`;
# the no-install route resolves to four words, `npx --yes --package=nostdb nostdb`; and a mapping
# that chains two commands contains the word twice, so there is no one place to put a prefix.
#
# Exit codes: 0 mapped, 1 the action needs a model and has no AI-free mapping, 2 unknown.
set -eu

# The resolved command, or the bare name when a caller is only inspecting the mapping.
NOSTDB=${NOSTDB:-nostdb}

[ "$#" -ge 1 ] || { echo "usage: dispatch.sh <action> [arguments...]" >&2; exit 2; }
action=$1
shift

# Every row here maps an action to the CLI commands that do its work, and the test asserts the
# correspondence with the shipped table in both directions: a table row with no mapping fails, and a
# mapping with no table row fails. A table that drifted from the dispatcher would describe a Skill that
# does not exist.
#
# An action is **not** required to be one CLI command, or to be named after one. `build` runs two, and
# `help` runs none. What every AI-free action must do is have the CLI do the work — the Skill composes
# commands and never computes an answer itself, because two implementations of one question is two
# answers and which one a user gets would depend on the surface they reached for.
case "$action" in
  help)
    # Not a command. `/nostdb help` describes *this Skill*, and the Skill is what knows — so it
    # answers from its own definition rather than resolving an Engine to ask one.
    #
    # Refused here rather than printing the text, so this script keeps one output contract: it prints a
    # command to run. An action that printed prose instead would make every caller check which kind of
    # output it got.
    echo "help is answered by the Skill; run scripts/help.sh, which needs no Engine" >&2
    exit 1
    ;;
  build)
    # A bare `/nostdb .` end to end: configure the project if it is not configured, then analyze the
    # whole tree and commit what was found, writing `.nostdb/settings.json` and `.nostdb/root.nostdb`.
    # The analysis is AI-free and always was — structural analysis of supported source spends no
    # external tokens, so this is the whole of `/nostdb .` and enrichment is a separate step on top.
    #
    # `init` is guarded rather than run unconditionally, because it refuses an already-configured
    # project and exits 2 so that a re-run cannot discard configuration. `/nostdb .` has to work the
    # second time as well as the first, and the guard is the settings file `init` itself writes.
    target=${1:-.}
    echo "[ -f $target/.nostdb/settings.json ] || $NOSTDB init $target; $NOSTDB build $target"
    ;;
  build-nost)
    # The same, materializing the canonical `.nost` afterwards.
    target=${1:-.}
    echo "[ -f $target/.nostdb/settings.json ] || $NOSTDB init $target; $NOSTDB build $target && $NOSTDB export --nost $target"
    ;;
  sync)
    echo "$NOSTDB sync ${1:-.}"
    ;;
  query-cypher)
    [ "$#" -ge 1 ] || { echo "query-cypher needs a statement" >&2; exit 2; }
    echo "$NOSTDB query $1"
    ;;
  view)
    echo "$NOSTDB view ${1:-.}"
    ;;
  plugin-add)
    [ "$#" -ge 1 ] || { echo "plugin-add needs a source" >&2; exit 2; }
    echo "$NOSTDB plugin add $1"
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
