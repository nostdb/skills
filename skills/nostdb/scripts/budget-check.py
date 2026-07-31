#!/usr/bin/env python3
"""Decides whether enrichment may start, from a plan document.

Reads `nostdb plan --format json` on standard input and prints one of `proceed`, `ask`, `skip`, or `refuse`,
with a reason on standard error.

The check compares the *top* of the estimate. A call that could exceed a hard limit never starts: comparing
the optimistic end would make the limit advisory in exactly the cases where it matters.

# The plan is parsed rather than scanned

This read four numbers with `tr -d ' \\n' | sed -n 's/.*"key":\\([0-9]*\\).*/\\1/p'`, and the comment beside it
called that a flat scan chosen over a dependency. It was not a scan of the document; it was a pattern matched
anywhere in the document with every space and newline removed first. Three ways that gives a wrong answer:

- a string value containing `"max_input_tokens":` matches, and a plan may carry paths and messages;
- the nested form assumed the inner key follows the outer within one `{}`, so any object between them broke it;
- `.*` is greedy, so the *last* match won rather than the intended one, which is why `head -1` was there and
  did nothing.

Python parses JSON in the standard library, so there is no dependency to weigh and no pattern to get right.

Exit codes: 0 proceed, 1 ask, 2 skip, 3 refuse, 4 the plan could not be read.
"""

from __future__ import annotations

import json
import sys

PROCEED, ASK, SKIP, REFUSE, UNREADABLE = 0, 1, 2, 3, 4


def answer(decision: str, reason: str, code: int) -> None:
    """One decision on stdout and its reason on stderr, which is the contract every caller reads."""
    print(decision)
    print(reason, file=sys.stderr)
    raise SystemExit(code)


def unreadable(reason: str) -> None:
    print(reason, file=sys.stderr)
    raise SystemExit(UNREADABLE)


def whole_number(value: object) -> int | None:
    """A count or a token figure, or `None` when the plan did not stated one as a number.

    A float is refused rather than truncated: a token count is a whole number, and a plan carrying 1.5 has a
    defect this should not paper over. A boolean is refused because `True` is an `int` in Python and a plan
    saying `"max_input_tokens": true` means nothing.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def main(argv: list[str]) -> None:
    interactive = (argv[0] if argv else "interactive") == "interactive"

    try:
        plan = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        unreadable(f"the plan is not readable JSON: {error}")
    if not isinstance(plan, dict):
        unreadable("the plan is not an object")

    candidates = whole_number(plan.get("semantic_candidates"))
    if candidates is None:
        unreadable("the plan states no candidate count")

    if candidates == 0:
        answer("proceed", "nothing is eligible for enrichment, so nothing is spent", PROCEED)

    # `ai_mode: off` is a refusal rather than a skip. The difference matters: a skip says nobody was asked,
    # and a refusal says somebody already answered.
    if plan.get("ai_mode") == "off":
        answer("refuse", "analysis.ai_mode is off", REFUSE)

    estimated = whole_number((plan.get("estimated_input_tokens") or {}).get("high"))
    limit = whole_number((plan.get("budget") or {}).get("max_input_tokens"))

    if limit is None:
        # No hard limit. The contract requires showing the estimate and asking once — and in a
        # non-interactive session there is nobody to ask, so enrichment is skipped rather than proceeding on
        # a default nobody chose.
        if interactive:
            shown = estimated if estimated is not None else "unknown"
            answer("ask", f"no token limit is configured; enrichment could reach {shown} tokens", ASK)
        answer("skip", "no token limit is configured and nobody can be asked", SKIP)

    if estimated is None:
        unreadable("the plan states no estimate")

    # The top of the band, not the bottom.
    if estimated > limit:
        answer("skip", f"the estimate could reach {estimated} and the limit is {limit}", SKIP)

    answer("proceed", f"the estimate tops out at {estimated} within a limit of {limit}", PROCEED)


if __name__ == "__main__":
    main(sys.argv[1:])
