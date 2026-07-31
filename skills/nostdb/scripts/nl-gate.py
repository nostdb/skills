#!/usr/bin/env python3
"""Decides what happens to a natural-language proposal.

A model produces a proposal: what kind of request it thinks this was, and the openCypher it generated. This
applies policy to that proposal, and the policy is the part that can be tested — a model's output is not
reproducible even in principle, but what is done with it is entirely deterministic.

Reads a proposal as JSON on standard input. Prints one of:

  execute   a read: show the statement, then run it
  confirm   a write: show the exact scope, and run nothing until somebody says so
  clarify   ambiguous: ask, and run nothing
  refuse    the proposal cannot be acted on at all

# The proposal is parsed rather than pattern-matched

Two members were read with `tr -d '\\n' | sed -n 's/.*"key"[[:space:]]*:[[:space:]]*"\\([^"]*\\)".*/\\1/p'`. That
took the *last* match, because a leading `.*` is greedy, and it stopped a value at the first `"` — so a
statement containing an escaped quote was truncated, and the part after it was dropped before the write clauses
were looked for. A truncated statement is the one input where this deciding "read" is worst.

Exit codes: 0 execute, 1 confirm, 2 clarify, 3 refuse, 4 the proposal could not be read.
"""

from __future__ import annotations

import json
import re
import sys

EXECUTE, CONFIRM, CLARIFY, REFUSE, UNREADABLE = 0, 1, 2, 3, 4

# The clauses the Engine's query subset treats as writes are CREATE, DELETE, DETACH, MERGE, REMOVE, and SET.
# This list covers all of them — DETACH only ever appears as DETACH DELETE — and adds DROP, which the subset
# does not support at all. Being conservative beyond the Engine is the right direction: the cost is a
# confirmation prompt for a statement that would have been refused anyway.
WRITE_CLAUSES = ("CREATE", "MERGE", "DELETE", "DETACH", "SET", "REMOVE", "DROP")

# A string literal in either quote, including one holding an escaped quote of its own. Stripped before the
# clauses are looked for, so a statement returning the text "DELETE" is a read.
LITERAL = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")


def answer(decision: str, reason: str, code: int) -> None:
    print(decision)
    print(reason, file=sys.stderr)
    raise SystemExit(code)


def unreadable(reason: str) -> None:
    print(reason, file=sys.stderr)
    raise SystemExit(UNREADABLE)


def names_a_clause(statement: str, clause: str) -> bool:
    """Whether an upper-cased statement names a clause as a word.

    Bounded by anything that is not a letter, which is what the shell's `(^|[^A-Z])…([^A-Z]|$)` meant: `SETTING`
    is not `SET`, and `n.set` is not either.
    """
    return re.search(rf"(?<![A-Z]){clause}(?![A-Z])", statement) is not None


def main(argv: list[str]) -> None:
    confirmed = (argv[0] if argv else "unconfirmed") == "confirmed"

    try:
        proposal = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        unreadable(f"the proposal is not readable JSON: {error}")
    if not isinstance(proposal, dict):
        unreadable("the proposal is not an object")

    kind = proposal.get("kind")
    kind = kind if isinstance(kind, str) else ""
    if not kind:
        unreadable("the proposal states no kind")

    if kind == "ambiguous":
        # Asked and not executed, even if a caller passed confirmation. Confirming a request nobody has stated
        # precisely is confirming the Skill's guess at it.
        answer("clarify", "the request has more than one reading; ask rather than pick one", CLARIFY)

    cypher = proposal.get("cypher")
    cypher = cypher if isinstance(cypher, str) else ""
    if not cypher:
        unreadable("the proposal states no statement")

    # What the statement *is*, not what the proposal says it is.
    #
    # This is the whole safety property here. A model that mislabels a DELETE as a read would otherwise have it
    # executed with no confirmation, and the label is the one part of a proposal that costs nothing to get
    # wrong. So the statement is inspected, and a write clause makes it a write however it was announced.
    stripped = LITERAL.sub("", cypher).upper()

    writes = any(names_a_clause(stripped, clause) for clause in WRITE_CLAUSES)
    # A procedure call can write without naming a clause, and this cannot tell which does. Treating every call
    # as a write is the conservative reading, and being asked to confirm a read is a smaller cost than a write
    # running unconfirmed.
    if names_a_clause(stripped, "CALL"):
        writes = True

    if not writes:
        if kind == "write":
            # The proposal claims a write and the statement does not write. Refused rather than downgraded: the
            # two disagree, and running the statement would mean deciding the model was wrong about its own
            # intent.
            answer("refuse", "the proposal claims a write and the statement writes nothing", REFUSE)
        answer("execute", "a read: show the statement, then run it", EXECUTE)

    if not confirmed:
        answer("confirm", "a write: show the exact scope and run nothing until somebody says so", CONFIRM)

    answer("execute", "a write, confirmed", EXECUTE)


if __name__ == "__main__":
    main(sys.argv[1:])
