#!/bin/sh
# Proves what the budget check decides, against plans a real `nostdb plan` produces.
#
# No model is called and none is needed: what is under test is the gate in front of the call,
# which is the whole of what can be tested here. A model's output is not reproducible even in
# principle, so the decision to call it is the part a fixture can pin.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
check="$here/../scripts/budget-check.sh"

failures=0
expect() {
  label=$1; plan=$2; mode=$3; want=$4
  got=$(printf '%s' "$plan" | "$check" "$mode" 2>/dev/null || true)
  if [ "$got" = "$want" ]; then
    echo "ok   $label"
  else
    echo "FAIL $label: expected [$want], got [$got]" >&2
    failures=$((failures + 1))
  fi
}

plan() {
  cat <<JSON
{"semantic_candidates": $1, "ai_mode": "$2",
 "estimated_input_tokens": {"low": 100, "high": $3},
 "budget": {"max_input_tokens": $4}}
JSON
}

no_limit() {
  cat <<JSON
{"semantic_candidates": $1, "ai_mode": "auto",
 "estimated_input_tokens": {"low": 100, "high": $2},
 "budget": {"max_cost_usd": null}}
JSON
}

expect "an estimate inside the limit proceeds"        "$(plan 5 auto 500 1000)"  interactive proceed
expect "an estimate at the limit proceeds"            "$(plan 5 auto 1000 1000)" interactive proceed
# The top of the band, not the bottom. Comparing the optimistic end would make the limit
# advisory in exactly the cases where it matters.
expect "an estimate that could exceed it does not"    "$(plan 5 auto 1001 1000)" interactive skip
expect "a zero limit permits no work at all"          "$(plan 5 auto 100 0)"     interactive skip

# A refusal is not a skip: a skip says nobody was asked, a refusal says somebody answered.
expect "ai_mode off refuses rather than skipping"     "$(plan 5 off 100 100000)" interactive refuse

expect "nothing eligible proceeds spending nothing"   "$(plan 0 auto 0 1000)"    interactive proceed
expect "nothing eligible proceeds even with ai off"   "$(plan 0 off 0 1000)"     interactive proceed

# No configured limit: ask once, and only where there is somebody to ask.
expect "no limit asks in an interactive session"      "$(no_limit 5 900)"        interactive ask
expect "no limit skips when nobody can be asked"      "$(no_limit 5 900)"        batch      skip

# A plan it cannot read is not treated as permission.
got=$(printf 'not a plan' | "$check" interactive 2>/dev/null || true)
if [ -z "$got" ]; then
  echo "ok   an unreadable plan grants nothing"
else
  echo "FAIL an unreadable plan produced [$got]" >&2
  failures=$((failures + 1))
fi

printf 'not a plan' | "$check" interactive >/dev/null 2>&1 && r=$? || r=$?
[ "$r" -eq 4 ] && echo "ok   an unreadable plan exits 4" || {
  echo "FAIL unreadable plan exited $r" >&2; failures=$((failures + 1)); }

# Against a plan the Engine actually produced.
#
# This is the check that found the defect the hand-written shapes above could not: the plan
# document had no `ai_mode`, so the refusal path was unreachable in reality while every
# fixture passed. A suite written only against shapes its author invented tests the author's
# idea of the document.
engine=${NOSTDB:-nostdb}
if command -v "$engine" >/dev/null 2>&1; then
  work=$(mktemp -d)
  trap 'rm -rf "$work"' EXIT
  printf 'def main(): pass\n' > "$work/app.py"
  "$engine" init "$work" >/dev/null 2>&1

  real=$("$engine" plan --format json --project "$work" 2>/dev/null)
  got=$(printf '%s' "$real" | "$check" interactive 2>/dev/null || true)
  check_real() {
    if [ "$2" = "$3" ]; then echo "ok   $1"; else
      echo "FAIL $1: expected [$3], got [$2]" >&2; failures=$((failures + 1)); fi
  }
  check_real "a real plan with no limit asks" "$got" "ask"

  printf '{"settings_version":1,"analysis":{"ai_mode":"off"}}' > "$work/.nostdb/settings.json"
  got=$("$engine" plan --format json --project "$work" 2>/dev/null | "$check" interactive 2>/dev/null || true)
  check_real "a real plan with ai_mode off refuses" "$got" "refuse"

  printf '{"settings_version":1,"analysis":{"max_input_tokens":1}}' > "$work/.nostdb/settings.json"
  got=$("$engine" plan --format json --project "$work" 2>/dev/null | "$check" interactive 2>/dev/null || true)
  check_real "a real plan over its limit skips" "$got" "skip"
else
  echo "skip no nostdb on the path; the real-plan checks did not run" >&2
fi

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "budget: every check passed"
