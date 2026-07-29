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

# How a command is told which project to work on.
#
# `build` and `plan` take `--project PATH`; every other path-taking command takes a positional. That is
# not a style choice. Release 0.1.0 **refuses** a positional path to `build`, a later build accepts one,
# and the two report byte-identical `--version --json` — so a positional worked against source and failed
# against the published Engine, and nothing in the compatibility check could tell them apart.
#
# `--project` is accepted by every version, so it is what is emitted.
project() {
  printf -- '--project %s' "$1"
}

# `init`, but only when the project is not configured.
#
# The guard stays in the emitted command, because the state can change between printing a command and
# running it. What changed is that `init` is left out entirely when the settings file is already there:
# somebody shown a command containing `init` reasonably reads it as "this will initialize", and being
# told that about a project configured weeks ago is how a correct guard reads as a bug.
configure() {
  [ -f "$1/.nostdb/settings.json" ] && return 0
  printf '[ -f %s/.nostdb/settings.json ] || %s init %s; ' "$1" "$NOSTDB" "$1"
}

# The container file a path names, whichever of the two ways it was named.
#
# Somebody asking about a database points either at the project or at the `.nostdb` folder itself,
# usually with the trailing slash a shell completed. `check` takes the container file, so both
# spellings have to arrive at one path.
#
# Decided from the text rather than by probing for what exists. State changes between printing a
# command and running it, and a path that depended on what was there at print time would emit a
# different command for the same argument depending on when it was asked.
container() {
  named=${1%/}
  case "$named" in
    .nostdb | */.nostdb) printf '%s/root.nostdb' "$named" ;;
    *) printf '%s/.nostdb/root.nostdb' "$named" ;;
  esac
}

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
    echo "$(configure "$target")$NOSTDB build $(project "$target")"
    ;;
  build-nost)
    # The same, materializing the canonical `.nost` afterwards.
    target=${1:-.}
    echo "$(configure "$target")$NOSTDB build $(project "$target") && $NOSTDB export --nost $target"
    ;;
  sync)
    echo "$NOSTDB sync ${1:-.}"
    ;;
  summary)
    # What a database holds, in five reads that write nothing. Every number is the Engine's: counting
    # the graph here would be a short awk script, and a second implementation of "how many nodes" is
    # a second answer to one question.
    #
    # The per-source count earns its place by reconciling the other two. `build_status` answers from
    # the root, a `MATCH` reads the union of the root and its links, so one link reports 5 nodes and
    # then breaks down 11 — and prose in this file cannot help whoever reads the output. Grouping,
    # not filtering: the subset has no `IS NULL`, so a `WHERE` scoping to the root is refused.
    #
    # `check` is last because it is the one call that fails on a sound report, exiting 3 on an error
    # diagnostic. Last means the counts are already out, so the failure answers "is this database
    # sound" instead of suppressing the summary that was asked for.
    #
    # Statements are quoted, so what is printed runs as one line. What the two pairs of numbers mean,
    # and why they differ, is in SKILL.md, where whoever renders the report reads.
    target=${1:-.}
    query="$NOSTDB query"
    totals='CALL nostdb.build_status()'
    by_source='MATCH (n) RETURN nostdb.link_alias(n) AS alias, count(n) AS total ORDER BY total DESC'
    of_nodes='MATCH (n) RETURN labels(n) AS labels, count(n) AS total ORDER BY total DESC, labels'
    of_edges='MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS total ORDER BY total DESC, type'
    echo "$query '$totals' --project $target && $query '$by_source' --project $target && $query '$of_nodes' --project $target && $query '$of_edges' --project $target && $NOSTDB check $(container "$target")"
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
  preset-check)
    # The Engine validates a preset, because a preset is a `.nost` document and the Engine is what reads
    # one. The Skill holds no validator: a second reader of the language is exactly what this boundary
    # forbids, and a malformed preset must fail before it is ever offered to a model.
    #
    # The name is passed through unchecked, the way a written statement is. Whether the file is there is the
    # Engine's answer to give, and asking the filesystem here would make the printed command depend on when
    # it was printed.
    [ "$#" -ge 1 ] || { echo "preset-check needs a preset name" >&2; exit 2; }
    echo "$NOSTDB check presets/$1.nost"
    ;;
  preset-apply|query-natural|enrich)
    # Named so the refusal is specific. Reporting these as unknown would suggest a typo,
    # when the truth is that they exist and need something this path cannot supply.
    #
    # `preset-apply` is here rather than beside `preset-check` for the reason that matters most about a
    # preset: a preset is a vocabulary, and **deriving a fact from one without a model would make this a
    # second analyzer** — reading annotations the Engine's own analyzers do not read. The interpretation is
    # the model's and the validation is the Engine's.
    echo "$action requires a model and has no AI-free mapping" >&2
    exit 1
    ;;
  *)
    echo "unknown action: $action" >&2
    exit 2
    ;;
esac
