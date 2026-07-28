#!/bin/sh
# Resolves the nostdb command a Skill should use, and prints it.
#
# The order is fixed by the product contract: project-local, then a compatible global, then
# a pinned npx. Nothing here installs anything, and nothing falls back to an unpinned
# version — a version resolved at run time is a version nobody reviewed.
#
# Prints the command on standard output and nothing else, so a caller can use the result
# directly. Diagnostics go to standard error.
#
# Exit codes: 0 resolved, 1 nothing compatible found, 2 used incorrectly.
set -eu

usage() {
  echo "usage: resolve-engine.sh <required-contract> <required-version> [pinned-version]" >&2
  exit 2
}

[ "$#" -ge 2 ] || usage
contract=$1
required=$2
pinned=${3:-}

# A candidate must answer `--version --json` and support the contract version asked for.
# A command that does not answer is not an old nostdb; it is not nostdb, because something
# on the path with the right name and the wrong behavior is worse than nothing.
compatible() {
  candidate=$1
  reply=$("$candidate" --version --json 2>/dev/null) || return 1
  # The argument is the *contract key*, which is what the version registry publishes and what every
  # document names: `nost_language_version`. The report answers with what a build supports, which is
  # a list, so its key is that plus an `s`. Asking for the singular key found nothing in a real
  # report, and every fake here agreed with the question rather than with the Engine.
  reported="${contract}s"
  echo "$reply" | grep -q "\"$reported\"" || return 1
  # The reply lists supported versions as a JSON array of numbers. A match must be on a
  # whole number, so that supporting 12 is not read as supporting 1.
  echo "$reply" \
    | tr -d ' \n' \
    | sed -n "s/.*\"$reported\":\[\([^]]*\)\].*/\1/p" \
    | tr ',' '\n' \
    | grep -qx "$required"
}

# 1. Project-local. A project that pinned a version did so on purpose, and a global
#    installation overriding it would mean one checkout giving two people different answers.
for candidate in ./node_modules/.bin/nostdb ./bin/nostdb; do
  if [ -x "$candidate" ] && compatible "$candidate"; then
    echo "$candidate"
    exit 0
  fi
done

# 2. A compatible global.
if global=$(command -v nostdb 2>/dev/null) && compatible "$global"; then
  echo "$global"
  exit 0
fi

# 3. A pinned npx, and only pinned.
if [ -n "$pinned" ] && command -v npx >/dev/null 2>&1; then
  echo "npx --yes --package=nostdb@$pinned nostdb"
  exit 0
fi

echo "no nostdb supporting $contract $required was found" >&2
echo "install one, or pass a pinned version to use npx" >&2
exit 1
