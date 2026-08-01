#!/usr/bin/env python3
"""Maps an AI-free Skill action to the nostdb command it invokes, and prints it.

This exists so there is exactly one answer to "what does this action do". The Skill is an extension of the CLI,
not a second engine: an AI-free action must call the same Core command the command surface calls, not an
equivalent one. Two implementations of one action is two answers to one question, and which a user gets would
depend on which surface they happened to reach for.

Printing the command rather than running it is deliberate. It makes the mapping testable without an Engine, and
it means a caller can show a user exactly what will run before anything does — which is what a
natural-language write is separately required to do.

# The command is substituted, not prefixed

`NOSTDB` holds the command `resolve-engine.py` printed, and defaults to `nostdb`. What is printed here is
therefore runnable as it stands.

It used to print the literal word `nostdb` and the definition said to run that "prefixed by the resolved
command". That does not compose. A project-local resolution gives `./node_modules/.bin/nostdb`, so prefixing
produces `./node_modules/.bin/nostdb nostdb build .`; the no-install route resolves to four words,
`npx --yes --package=nostdb nostdb`; and a mapping that chains two commands contains the word twice, so there
is no one place to put a prefix.

Exit codes: 0 mapped, 1 the action needs a model and has no AI-free mapping, 2 unknown.
"""

from __future__ import annotations

import os
import sys

# The resolved command, or the bare name when a caller is only inspecting the mapping.
NOSTDB = os.environ.get("NOSTDB") or "nostdb"

# Actions that exist and need something this path cannot supply. Named so the refusal is specific: reporting
# them as unknown would suggest a typo, when the truth is they exist and need a model.
#
# `preset-apply` is here rather than beside `preset-check` for the reason that matters most about a preset: a
# preset is a vocabulary, and **deriving a fact from one without a model would make this a second analyzer** —
# reading annotations the Engine's own analyzers do not read. The interpretation is the model's and the
# validation is the Engine's.
# `scan-ai` is here because it is the whole of `/nostdb . --scan=ai`: the analyzers are not run, so there is
# nothing for an AI-free path to fall back to. An action that quietly built with the analyzers instead would
# report a result the caller explicitly did not ask for.
NEEDS_A_MODEL = ("preset-apply", "query-natural", "scan-ai")

# Every action this dispatcher knows, mapped or not.
#
# Load-bearing rather than a list for a reader: an action absent from here is refused as unknown before any
# branch is reached, so a branch that is not named here is unreachable and one named here with no branch falls
# through to the same refusal. That is what keeps this from drifting into a second, decorative answer to "what
# actions exist".
#
# The shell version had no such list — a `case` label was the only record — and the suite discovered them by
# grepping those labels and then *running* each. Running each is the part worth keeping, because an action is
# no longer required to emit a command: `help` is a label that maps nothing. So this replaces the grep and not
# the running.
ACTIONS = (
    "help",
    "build",
    "export",
    "convert",
    "summary",
    "query-cypher",
    "view",
    "plugin-add",
    "check",
    "preset-check",
    *NEEDS_A_MODEL,
)


def refuse(message: str, code: int) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def project(target: str) -> str:
    """How a command is told which project to work on.

    `build` and `plan` take `--project PATH`; every other path-taking command takes a positional. That is not a
    style choice. Release 0.1.0 **refuses** a positional path to `build`, a later build accepts one, and the two
    report byte-identical `--version --json` — so a positional worked against source and failed against the
    published Engine, and nothing in the compatibility check could tell them apart.

    `--project` is accepted by every version, so it is what is emitted.
    """
    return f"--project {target}"


def configure(target: str) -> str:
    """`init`, but only when the project is not configured.

    The guard stays in the emitted command, because the state can change between printing a command and running
    it. What changed is that `init` is left out entirely when the settings file is already there: somebody shown
    a command containing `init` reasonably reads it as "this will initialize", and being told that about a
    project configured weeks ago is how a correct guard reads as a bug.
    """
    if os.path.isfile(os.path.join(target, ".nostdb", "settings.json")):
        return ""
    return f"[ -f {target}/.nostdb/settings.json ] || {NOSTDB} init {target}; "


def container(named: str) -> str:
    """The container file a path names, whichever of the two ways it was named.

    Somebody asking about a database points either at the project or at the `.nostdb` folder itself, usually
    with the trailing slash a shell completed. `check` takes the container file, so both spellings have to
    arrive at one path.

    Decided from the text rather than by probing for what exists. State changes between printing a command and
    running it, and a path that depended on what was there at print time would emit a different command for the
    same argument depending on when it was asked.
    """
    named = named.rstrip("/") or named
    if named == ".nostdb" or named.endswith("/.nostdb"):
        return f"{named}/root.nostdb"
    return f"{named}/.nostdb/root.nostdb"


def summary(target: str) -> str:
    """What a database holds, in five reads that write nothing.

    Every number is the Engine's: counting the graph here would be a short awk script, and a second
    implementation of "how many nodes" is a second answer to one question.

    The per-source count earns its place by reconciling the other two. `build_status` answers from the root, a
    `MATCH` reads the union of the root and its links, so one link reports 5 nodes and then breaks down 11 — and
    prose in this file cannot help whoever reads the output. Grouping, not filtering: the subset has no
    `IS NULL`, so a `WHERE` scoping to the root is refused.

    `check` is last because it is the one call that fails on a sound report, exiting 3 on an error diagnostic.
    Last means the counts are already out, so the failure answers "is this database sound" instead of
    suppressing the summary that was asked for.

    Statements are quoted, so what is printed runs as one line. What the two pairs of numbers mean, and why they
    differ, is in `SKILL.md`, where whoever renders the report reads.
    """
    query = f"{NOSTDB} query"
    statements = (
        "CALL nostdb.build_status()",
        "MATCH (n) RETURN nostdb.link_alias(n) AS alias, count(n) AS total ORDER BY total DESC",
        "MATCH (n) RETURN labels(n) AS labels, count(n) AS total ORDER BY total DESC, labels",
        "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS total ORDER BY total DESC, type",
    )
    reads = [f"{query} '{statement}' --project {target}" for statement in statements]
    reads.append(f"{NOSTDB} check {container(target)}")
    return " && ".join(reads)


def main(argv: list[str]) -> None:
    if not argv:
        refuse("usage: dispatch.py <action> [arguments...]", 2)
    action, rest = argv[0], argv[1:]
    if action not in ACTIONS:
        refuse(f"unknown action: {action}", 2)
    first = rest[0] if rest else None

    # Every branch here maps an action to the CLI commands that do its work, and the test asserts the
    # correspondence with the shipped table in both directions: a table row with no mapping fails, and a mapping
    # with no table row fails. A table that drifted from the dispatcher would describe a Skill that does not
    # exist.
    #
    # An action is **not** required to be one CLI command, or to be named after one. `build` runs two, and `help`
    # runs none. What every AI-free action must do is have the CLI do the work — the Skill composes commands and
    # never computes an answer itself, because two implementations of one question is two answers and which one
    # a user gets would depend on the surface they reached for.
    if action == "help":
        # Not a command. `/nostdb help` describes *this Skill*, and the Skill is what knows — so it answers from
        # its own definition rather than resolving an Engine to ask one.
        #
        # Refused here rather than printing the text, so this script keeps one output contract: it prints a
        # command to run. An action that printed prose instead would make every caller check which kind of
        # output it got.
        refuse("help is answered by the Skill; run scripts/help.py, which needs no Engine", 1)

    if action == "build":
        # A bare `/nostdb .` end to end: configure the project if it is not configured, then analyze the whole
        # tree and commit what was found, writing `.nostdb/settings.json` and `.nostdb/root.nostdb`. The
        # analysis is AI-free and always was — structural analysis of supported source spends no external
        # tokens, so this is the whole of `/nostdb .` and enrichment is a separate step on top.
        #
        # `init` is guarded rather than run unconditionally, because it refuses an already-configured project
        # and exits 2 so that a re-run cannot discard configuration. `/nostdb .` has to work the second time as
        # well as the first, and the guard is the settings file `init` itself writes.
        target = first or "."
        print(f"{configure(target)}{NOSTDB} build {project(target)}")
        return

    if action == "export":
        # Writes the canonical `.nost` from what is already in the database, and builds nothing.
        #
        # It used to be `build-nost`, which emitted `build && export` behind a flag on `/nostdb .`. Two things
        # were wrong with that. A flag on a build reads as "this build now materializes", and it does not —
        # `export` writes the document once and the Engine warns that nothing will keep it current, because
        # `database.nost` stays false and no CLI command sets it. And somebody who only wanted the document had
        # the whole tree re-analyzed to get it.
        #
        # No `configure` guard, unlike `build`. The Engine finds the nearest *configured* project itself and
        # says so when there is none, and initializing a project as a side effect of asking for a document would
        # configure a directory somebody only wanted to read out of.
        #
        # `--nost` is spelled here rather than left to the Engine's default, and that is the point of the
        # surface's default rather than a duplication of it. The CLI requires the flag so a later representation
        # cannot silently change what a bare `export` means; emitting it keeps that true no matter what the
        # surface later spells, and a bare `export` never reaches the Engine.
        print(f"{NOSTDB} export --nost {first or '.'}")
        return

    if action == "convert":
        # `.nost` <-> `.nostdb`, in whichever direction the extensions name. The Engine decides which, and
        # refuses two identical extensions because that is a copy rather than a conversion.
        #
        # Both operands are required. Defaulting either would invent a path somebody did not name, and the one
        # it would invent is an output — a command that writes somewhere nobody asked for is worse than a
        # command that refuses.
        #
        # `--replace` is passed through when a caller asked for it, and never added. The Engine refuses an
        # existing output without it, and a Skill that supplied the flag on their behalf would turn a refusal
        # somebody was meant to see into a file they did not know they lost.
        if len(rest) < 2:
            refuse("convert needs an input and an output", 2)
        if len(rest) == 2:
            print(f"{NOSTDB} convert {rest[0]} {rest[1]}")
            return
        if len(rest) == 3 and rest[2] == "--replace":
            print(f"{NOSTDB} convert {rest[0]} {rest[1]} --replace")
            return
        refuse("convert takes an input, an output, and optionally --replace", 2)

    if action == "summary":
        print(summary(first or "."))
        return

    if action == "query-cypher":
        if not rest:
            refuse("query-cypher needs a statement", 2)
        print(f"{NOSTDB} query {rest[0]}")
        return

    if action == "view":
        print(f"{NOSTDB} view {first or '.'}")
        return

    if action == "plugin-add":
        if not rest:
            refuse("plugin-add needs a source", 2)
        print(f"{NOSTDB} plugin add {rest[0]}")
        return

    if action == "check":
        # Validates any `.nost` or `.nostdb` the caller names, which is what closes the `--scan=ai` loop: the
        # model writes a candidate document and the Engine says whether it reads.
        #
        # A path rather than a preset name, because a candidate is somewhere the caller chose. `preset-check`
        # below resolves a name against this Skill's own folder and is a different question.
        if not rest:
            refuse("check needs a path", 2)
        print(f"{NOSTDB} check {rest[0]}")
        return

    if action == "preset-check":
        # The Engine validates a preset, because a preset is a `.nost` document and the Engine is what reads
        # one. The Skill holds no validator: a second reader of the language is exactly what this boundary
        # forbids, and a malformed preset must fail before it is ever offered to a model.
        #
        # The name is passed through unchecked, the way a written statement is. Whether the file is there is the
        # Engine's answer to give, and asking the filesystem here would make the printed command depend on when
        # it was printed.
        if not rest:
            refuse("preset-check needs a preset name", 2)
        print(f"{NOSTDB} check presets/{rest[0]}.nost")
        return

    if action in NEEDS_A_MODEL:
        refuse(f"{action} requires a model and has no AI-free mapping", 1)

    refuse(f"unknown action: {action}", 2)


if __name__ == "__main__":
    main(sys.argv[1:])
