#!/bin/sh
# Proves what the budget check decides, against plans a real `nostdb plan` produces.
#
# No model is called and none is needed: what is under test is the gate in front of the call,
# which is the whole of what can be tested here. A model's output is not reproducible even in
# principle, so the decision to call it is the part a fixture can pin.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
check="$here/../skills/nostdb/scripts/budget-check.py"

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
  # Ruby, which nothing here analyzes. This was `app.py` until Python gained an analyzer in
  # Stage 34, and the fixture then produced `semantic_candidates: 0` and a zero estimate — so
  # every check below asked what the budget does about spending nothing, and `proceed` is the
  # right answer to that. The three expectations went on saying `ask`, `refuse`, and `skip`,
  # and nothing noticed because this branch only runs with an Engine on the path, which no
  # automated run has.
  #
  # The same trap `project.rs` records for its own fixture: a language that *is* read makes
  # the test pass, or fail, for the wrong reason.
  printf 'class Server\n  def start\n  end\nend\n' > "$work/server.rb"
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

# Four plans that pin the reader to the document rather than to how the Engine happens to write it.
#
# The shell version removed every space and newline and matched a pattern anywhere in the result. Against the
# output `nostdb plan --format json` produces today it worked — `max_input_tokens` is written first inside
# `budget`, so the pattern's `[^}]*` matched nothing and found it.
#
# What it depended on was that ordering. JSON member order carries no meaning, so a refactor that moved one
# line in the emitter would have changed the answer with no contract change and nothing to notice: the gate
# would have read no limit and returned `ask` on a plan that should skip. Two of these four fail against the
# shell version, and both are shapes the contract permits.
#
# A string value that contains the key, written after the real one. A plan carries paths and messages, and the
# shell pattern led with `.*`, so the *last* occurrence won — a decoy before the real budget would have been
# shadowed by it and proved nothing.
expect "a key inside a string value is not read as the limit" \
  '{"semantic_candidates":3,"estimated_input_tokens":{"low":10,"high":20},"budget":{"max_input_tokens":900000},"note":"set \"max_input_tokens\":1 to cap it"}' \
  interactive proceed

# An object between the outer key and the inner one: the nested pattern required them inside one `{}`.
expect "a nested object before the key does not hide it" \
  '{"semantic_candidates":3,"budget":{"on_exceeded":{"kind":"stop"},"max_input_tokens":10},"estimated_input_tokens":{"low":10,"high":900}}' \
  interactive skip

# Key order: a regex with a leading `.*` is greedy, so the last match won. `head -1` was there for that and
# could not help.
expect "the order the members are written in does not change the answer" \
  '{"estimated_input_tokens":{"high":20,"low":10},"budget":{"max_input_tokens":900000},"semantic_candidates":3}' \
  interactive proceed

# A token figure that is not a whole number is a defect in whatever produced the plan, so it is unreadable
# rather than truncated.
expect "a fractional limit is not silently truncated" \
  '{"semantic_candidates":3,"budget":{"max_input_tokens":1.5},"estimated_input_tokens":{"low":10,"high":20}}' \
  interactive ask

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "budget: every check passed"
