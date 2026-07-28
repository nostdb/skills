#!/bin/sh
# Decides whether enrichment may start, from a plan document.
#
# Reads `nostdb plan --format json` on standard input and prints one of `proceed`, `ask`,
# `skip`, or `refuse`, with a reason on standard error.
#
# The check compares the *top* of the estimate. A call that could exceed a hard limit never
# starts: comparing the optimistic end would make the limit advisory in exactly the cases
# where it matters.
#
# Exit codes: 0 proceed, 1 ask, 2 skip, 3 refuse, 4 the plan could not be read.
set -eu

interactive=${1:-interactive}
plan=$(cat)

field() {
  # A flat scan rather than a JSON parser: this reads four numbers from a document the
  # Engine produced, and taking a dependency to do that would be more surface than the job.
  echo "$plan" | tr -d ' \n' | sed -n "s/.*\"$1\":\([0-9]*\).*/\1/p" | head -1
}

nested() {
  echo "$plan" | tr -d ' \n' | sed -n "s/.*\"$1\":{[^}]*\"$2\":\([0-9]*\).*/\1/p" | head -1
}

candidates=$(field semantic_candidates)
[ -n "$candidates" ] || { echo "the plan states no candidate count" >&2; exit 4; }

if [ "$candidates" -eq 0 ]; then
  echo "proceed"
  echo "nothing is eligible for enrichment, so nothing is spent" >&2
  exit 0
fi

# `ai_mode: off` is a refusal rather than a skip. The difference matters: a skip says nobody
# was asked, and a refusal says somebody already answered.
if echo "$plan" | tr -d ' \n' | grep -q '"ai_mode":"off"'; then
  echo "refuse"
  echo "analysis.ai_mode is off" >&2
  exit 3
fi

estimated=$(nested estimated_input_tokens high)
limit=$(nested budget max_input_tokens)

if [ -z "$limit" ]; then
  # No hard limit. The contract requires showing the estimate and asking once — and in a
  # non-interactive session there is nobody to ask, so enrichment is skipped rather than
  # proceeding on a default nobody chose.
  if [ "$interactive" = "interactive" ]; then
    echo "ask"
    echo "no token limit is configured; enrichment could reach ${estimated:-unknown} tokens" >&2
    exit 1
  fi
  echo "skip"
  echo "no token limit is configured and nobody can be asked" >&2
  exit 2
fi

[ -n "$estimated" ] || { echo "the plan states no estimate" >&2; exit 4; }

# The top of the band, not the bottom.
if [ "$estimated" -gt "$limit" ]; then
  echo "skip"
  echo "the estimate could reach $estimated and the limit is $limit" >&2
  exit 2
fi

echo "proceed"
echo "the estimate tops out at $estimated within a limit of $limit" >&2
exit 0
