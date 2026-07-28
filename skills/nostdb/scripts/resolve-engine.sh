#!/bin/sh
# Resolves the nostdb command a Skill should use, and prints it.
#
# The order is fixed by the product contract: project-local, then a compatible global. Both are
# cheap: a file test, then one `--version --json` on the first candidate that exists.
#
# # Why npx is no longer a silent third step
#
# It used to be. Passing a pinned version made `npx --yes --package=nostdb@<version> nostdb` the
# automatic answer whenever nothing was installed, so every action paid npx's fetch and start-up
# cost and nobody had chosen to. Resolution looked slow; what was slow was the command resolution
# handed back.
#
# npx is still available and still pinned. It is now one of three things a caller can *choose* when
# nothing is installed, and the choice is remembered so the question is asked once.
#
# # The decision, and where it is remembered
#
# With nothing installed and no remembered choice:
#
#   - an interactive session is asked, and the answer is stored;
#   - a non-interactive one exits 1 with the exact commands, unchanged. A script that paused for a
#     prompt nobody could answer would hang, and one that installed software unasked is worse.
#
# The choice lives in a single-line file, `~/.nostdb/skill-engine` by default. It records a decision
# a person made, not a resolved path: a cached path would be a lie the moment the Engine was
# installed, upgraded, or removed, and re-probing costs one process.
#
# Exit codes: 0 resolved, 1 nothing compatible and no decision, 2 used incorrectly,
#             3 the caller chose to continue with no Engine.
set -eu

usage() {
  echo "usage: resolve-engine.sh <required-contract> <required-version> [pinned-version]" >&2
  exit 2
}

[ "$#" -ge 2 ] || usage
contract=$1
required=$2
pinned=${3:-}

# Overridable so a test never touches a real home directory, and so a CI run can state the decision
# up front instead of being asked.
state=${NOSTDB_SKILL_STATE:-$HOME/.nostdb/skill-engine}
choice=${NOSTDB_SKILL_ENGINE_CHOICE:-}

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
# 2. A compatible global.
#
# Tried in one pass, stopping at the first that answers, so an installed Engine costs a single
# process rather than one per candidate.
resolve_installed() {
  for candidate in ./node_modules/.bin/nostdb ./bin/nostdb; do
    if [ -x "$candidate" ] && compatible "$candidate"; then
      echo "$candidate"
      return 0
    fi
  done
  if global=$(command -v nostdb 2>/dev/null) && compatible "$global"; then
    echo "$global"
    return 0
  fi
  return 1
}

if found=$(resolve_installed); then
  echo "$found"
  exit 0
fi

# Nothing installed answers for this contract. Everything below is about the decision.

remember() {
  directory=$(dirname "$state")
  mkdir -p "$directory" 2>/dev/null || return 0
  # Written whole and moved into place, so a reader sees one decision or the other. A partial line
  # would be a decision nobody made.
  printf '%s\n' "$1" > "$state.partial" 2>/dev/null || return 0
  mv "$state.partial" "$state" 2>/dev/null || rm -f "$state.partial"
}

install_commands() {
  echo "  npm install --global nostdb${pinned:+@$pinned}" >&2
  echo "  brew install nostdb/tap/nostdb" >&2
  if [ -n "$pinned" ]; then
    echo "  npx --yes --package=nostdb@$pinned nostdb   # no permanent install" >&2
  fi
}

# One spelling table for every source of the decision — a prompt, the environment, and the stored
# file — so `NOSTDB_SKILL_ENGINE_CHOICE=i` and a stored `install` cannot mean different things.
normalize() {
  case $1 in
    i | I | install) echo install ;;
    x | X | npx) echo npx ;;
    n | N | no | none) echo none ;;
    *) echo "" ;;
  esac
}

# A remembered choice, or one the environment states, is honored without asking again.
if [ -z "$choice" ] && [ -r "$state" ]; then
  choice=$(head -n 1 "$state" 2>/dev/null | tr -d ' \t\r\n')
fi
choice=$(normalize "$choice")

# Asked only when a person can answer. `set -eu` would abort on a read at end-of-input, and a
# script blocked on a prompt is worse than one that refuses.
if [ -z "$choice" ] && [ -t 0 ] && [ -t 2 ]; then
  echo "no installed nostdb supports $contract $required." >&2
  echo >&2
  echo "  [i] install it globally${pinned:+ (pinned to $pinned)}" >&2
  if [ -n "$pinned" ]; then
    echo "  [x] run it with a pinned npx each time, installing nothing" >&2
  fi
  echo "  [n] continue without an Engine" >&2
  echo >&2
  printf 'choice, remembered for next time [i/%sn]: ' "${pinned:+x/}" >&2
  if IFS= read -r answer; then
    choice=$(normalize "$answer")
    # An unreadable answer is not remembered. Storing a guess would make the next run act on
    # something nobody chose, and this way the question is simply asked again.
    if [ -n "$choice" ]; then
      remember "$choice"
    fi
  fi
fi

case $choice in
  npx)
    if [ -z "$pinned" ]; then
      echo "the remembered choice is npx, and no pinned version was passed" >&2
      echo "an unpinned version is a version nobody reviewed, so it is refused" >&2
      exit 1
    fi
    echo "npx --yes --package=nostdb@$pinned nostdb"
    exit 0
    ;;

  install)
    # Pinned only. An unpinned install is the fallback the product contract forbids, and a
    # remembered "yes" is consent to install a reviewed version rather than to whatever is newest.
    if [ -z "$pinned" ]; then
      echo "installing needs a pinned version, and none was passed" >&2
      echo "an unpinned install is a version nobody reviewed, so it is refused" >&2
      exit 1
    fi
    if ! command -v npm >/dev/null 2>&1; then
      echo "npm is not on the path, so this cannot install nostdb" >&2
      install_commands
      exit 1
    fi
    # Echoed before it runs. Installing software is a visible act even when it was agreed to once.
    echo "installing nostdb@$pinned globally, as chosen earlier" >&2
    echo "  npm install --global nostdb@$pinned" >&2
    if ! npm install --global "nostdb@$pinned" >&2; then
      echo "the install failed; nothing was resolved" >&2
      exit 1
    fi
    # Re-probed rather than assumed. An install that reported success and left nothing usable is
    # exactly the case a caller must not be told is fine.
    if found=$(resolve_installed); then
      echo "$found"
      exit 0
    fi
    echo "nostdb@$pinned installed and still does not support $contract $required" >&2
    exit 1
    ;;

  none)
    echo "continuing with no Engine, as chosen earlier" >&2
    echo "actions that need one will report what they could not do" >&2
    exit 3
    ;;
esac

echo "no nostdb supporting $contract $required was found" >&2
echo "install one of these, or re-run interactively to choose and have it remembered:" >&2
install_commands
echo "to state the choice without a prompt, set NOSTDB_SKILL_ENGINE_CHOICE to i, x, or n" >&2
exit 1
