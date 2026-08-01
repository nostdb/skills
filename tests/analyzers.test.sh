#!/bin/sh
# Discovery of the analyzer Skills installed beside `nostdb`, and the announcement for using one.
#
# What this pins is that discovery is **discovery**: no path to a sibling, no list of names, and a correct
# answer beside none. A Skill that hard-coded a sibling would work in this repository and fail in every
# install, which is the failure the layout rule exists to prevent.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
skill="$here/../skills/nostdb"
analyzers="$skill/scripts/analyzers.py"

failures=0
check() {
  if [ "$2" = "$3" ]; then
    echo "ok   $1"
  else
    echo "FAIL $1: expected [$3], got [$2]" >&2
    failures=$((failures + 1))
  fi
}

# The Skill holds no list of names: a Skill nobody has written yet is found the same way.
#
# Asserted by inventing one rather than by grepping for names — the docstring has to be able to say
# `nostdb-analyzer-springboot` while explaining what this does, and a check forbidding that is one people
# learn to work around. Behaviour is the thing that matters anyway: a hard-coded list could not find this.
invented=$(mktemp -d)
mkdir -p "$invented/nostdb/scripts" "$invented/nostdb-analyzer-invented"
cp "$analyzers" "$invented/nostdb/scripts/"
printf -- '---\nname: nostdb-analyzer-invented\ndescription: A framework nobody has written a Skill for yet.\n---\n' \
  > "$invented/nostdb-analyzer-invented/SKILL.md"
found=$("$invented/nostdb/scripts/analyzers.py" 2>/dev/null)
case "$found" in
  *nostdb-analyzer-invented*) echo "ok   an analyzer this repository never heard of is found" ;;
  *) echo "FAIL a Skill invented at run time was not found: [$found]" >&2; failures=$((failures + 1)) ;;
esac
check "and it can be announced" \
  "$("$invented/nostdb/scripts/analyzers.py" using invented | cut -d, -f1)" \
  "using nostdb-analyzer-invented"
rm -rf "$invented"

# This repository has one, so it is found, and its description comes from its own definition rather than a
# copy here — a copy is the thing that goes stale while nobody is reading it.
listed=$("$analyzers" 2>/dev/null || echo FAILED)
case "$listed" in
  *nostdb-analyzer-springboot*) echo "ok   the installed analyzer is found" ;;
  *) echo "FAIL listing produced [$listed]" >&2; failures=$((failures + 1)) ;;
esac
declared=$(sed -n 's/^description: //p' "$here/../skills/nostdb-analyzer-springboot/SKILL.md" | head -1)
case "$listed" in
  *"$declared"*) echo "ok   and described in its own words" ;;
  *) echo "FAIL the description is not the sibling's own" >&2; failures=$((failures + 1)) ;;
esac

# Both spellings of one name, because a person types the short one and a document names the long one.
check "the short name locates it" \
  "$(basename "$("$analyzers" path springboot)")" "nostdb-analyzer-springboot"
check "and so does the full name" \
  "$(basename "$("$analyzers" path nostdb-analyzer-springboot)")" "nostdb-analyzer-springboot"

# The announcement is one sentence, and it names the Skill.
announced=$("$analyzers" using springboot)
case "$announced" in
  "using nostdb-analyzer-springboot,"*) echo "ok   using announces the Skill by name" ;;
  *) echo "FAIL the announcement reads [$announced]" >&2; failures=$((failures + 1)) ;;
esac

# And it refuses a Skill that is not installed. This is the half that is about honesty: announcing a
# vocabulary nobody has would claim a reading nobody performed, and the output would look like the real one.
"$analyzers" using django >/dev/null 2>&1 && r=$? || r=$?
check "an uninstalled Skill is not announced" "$r" "1"
"$analyzers" path django >/dev/null 2>&1 && r=$? || r=$?
check "and has no path" "$r" "1"
"$analyzers" frobnicate >/dev/null 2>&1 && r=$? || r=$?
check "an unknown subcommand exits 2" "$r" "2"

# Installed alone, it answers rather than failing. An analyzer Skill is optional, and `/nostdb` works with the
# vocabulary it ships itself — so "none installed" is an answer, not an error.
alone=$(mktemp -d)
mkdir -p "$alone/nostdb/scripts"
cp "$analyzers" "$alone/nostdb/scripts/"
"$alone/nostdb/scripts/analyzers.py" >/dev/null 2>&1 && r=$? || r=$?
check "with no analyzer installed, listing still succeeds" "$r" "0"
check "and reports nothing on stdout" "$("$alone/nostdb/scripts/analyzers.py" 2>/dev/null)" ""
"$alone/nostdb/scripts/analyzers.py" using springboot >/dev/null 2>&1 && r=$? || r=$?
check "and refuses to announce one that is not there" "$r" "1"
rm -rf "$alone"

# A directory matching the prefix with no usable definition is skipped rather than offered: it is not a Skill
# anything can select, and naming it would offer one that cannot be used.
partial=$(mktemp -d)
mkdir -p "$partial/nostdb/scripts" "$partial/nostdb-analyzer-broken"
cp "$analyzers" "$partial/nostdb/scripts/"
check "a folder with no SKILL.md is not offered" \
  "$("$partial/nostdb/scripts/analyzers.py" 2>/dev/null)" ""
rm -rf "$partial"

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "analyzers: every check passed"
