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
#   - an interactive session is asked once — install it, or do not install and run it with npx — and
#     the answer holds for the rest of that session;
#   - a non-interactive one exits 1 with the exact commands, unchanged. A script that paused for a
#     prompt nobody could answer would hang, and one that installed software unasked is worse.
#
# The choice is remembered for the **session** that made it, not for ever, and it records a decision
# a person made rather than a resolved path: a cached path would be a lie the moment the Engine was
# installed, upgraded, or removed, and re-probing costs one process.
#
# The question is asked with a list the arrow keys move through, falling back to a typed answer on a
# terminal that will not enter raw mode.
#
# Exit codes: 0 resolved, 1 nothing compatible and no decision, 2 used incorrectly,
#             3 the caller chose to continue with no Engine, 130 the prompt was interrupted.
set -eu

usage() {
  echo "usage: resolve-engine.sh <required-contract> <required-version> [pinned-version]" >&2
  exit 2
}

[ "$#" -ge 2 ] || usage
contract=$1
required=$2
pinned=${3:-}

# The decision is remembered for the session that made it, not for ever.
#
# A permanent answer is the wrong lifetime for this question. Somebody who chose "no Engine" to get
# through one afternoon should not still be living with it next week, and somebody who installed one
# since is asked nothing either way — an installed Engine never consults the decision at all.
#
# The key is the POSIX session, which is what "session" means and is shared by every process in one
# terminal. Where there is no controlling terminal `ps` reports 0, and the parent shell stands in:
# repeated calls from one shell agree, and a new shell asks again. The file lives in the temporary
# directory so the operating system clears it, rather than accumulating one file per session for ever
# under a home directory.
session_key() {
  sid=$(ps -o sess= -p $$ 2>/dev/null | tr -d ' \t\n') || sid=
  if [ -n "$sid" ] && [ "$sid" != "0" ]; then
    echo "$sid"
  else
    echo "shell${PPID:-0}"
  fi
}

# Overridable so a test never touches real state, and so a CI run can state the decision up front
# instead of being asked.
state=${NOSTDB_SKILL_STATE:-${TMPDIR:-/tmp}/nostdb-skill-engine.$(session_key)}
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

# Nothing installed answers for this contract.

# On Windows there is nothing to offer, and saying so beats an install that cannot work.
#
# NostDB publishes four targets, all macOS and Linux. Windows is recorded as intended and not
# buildable: `nostdb-server` implements only the Unix domain socket while the protocol contract
# specifies a named pipe for Windows, so nothing in the product compiles there yet.
#
# A shell that reports MINGW, MSYS, or CYGWIN is a POSIX layer on Windows, which is the only way this
# script is running there at all. WSL reports Linux and is a supported platform, so it is not caught.
case $(uname -s 2>/dev/null || echo unknown) in
  MINGW* | MSYS* | CYGWIN*)
    echo "NostDB publishes no Windows build, so there is nothing to install or run here" >&2
    echo "the daemon implements only the Unix socket, and nothing in the product compiles for Windows yet" >&2
    echo "run this under WSL, which reports Linux and is a published target" >&2
    exit 1
    ;;
esac

# Everything below is about the decision.

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
  echo "  npx --yes --package=nostdb${pinned:+@$pinned} nostdb   # no permanent install" >&2
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
stated=$(normalize "$choice")
if [ -z "$stated" ] && [ -r "$state" ]; then
  choice=$(head -n 1 "$state" 2>/dev/null | tr -d ' \t\r\n')
  choice=$(normalize "$choice")
else
  choice=$stated
  # Stored as well as honored. The prompt below is unreachable without a terminal, which is exactly
  # how a Skill is normally run — an agent invokes it — so the environment is the *usual* way a
  # decision arrives, not an escape hatch. Remembering it is what makes one question cover a session
  # instead of the caller passing the answer on every call.
  if [ -n "$choice" ]; then
    remember "$choice"
  fi
fi

# The options, as `key|label` lines. sh has no arrays, and two parallel lists get out of step the
# first time somebody edits one of them.
options="install|Install nostdb${pinned:+@$pinned} globally with npm
npx|Do not install; run it with npx each time${pinned:+ (pinned to $pinned)}"
option_count=$(printf '%s\n' "$options" | wc -l | tr -d ' ')

# One keypress, named. Read as hex so a byte that is not text cannot be mistaken for one.
#
# An arrow key arrives as three bytes, escape then `[` then a letter, so escape reads two more. `j`
# and `k` move too: somebody who lives in a pager expects them to, and it costs two lines.
read_key() {
  first=$(dd bs=1 count=1 2>/dev/null | od -An -tx1 | tr -d ' \t\n')
  case $first in
    1b)
      rest=$(dd bs=1 count=2 2>/dev/null | od -An -tx1 | tr -d ' \t\n')
      case $rest in
        5b41) echo up ;;
        5b42) echo down ;;
        *) echo other ;;
      esac
      ;;
    0a | 0d) echo enter ;;
    20) echo enter ;;
    6b) echo up ;;
    6a) echo down ;;
    03 | 71) echo quit ;;
    "") echo quit ;;
    *) echo other ;;
  esac
}

# Drawn on standard error. Standard output carries the resolved command and nothing else, so a caller
# can use it directly — a menu printed there would become the command.
draw_options() {
  index=1
  printf '%s\n' "$options" | while IFS='|' read -r key label; do
    if [ "$index" = "$selected" ]; then
      printf '  \033[1m[x] %s\033[0m\n' "$label" >&2
    else
      printf '  [ ] %s\n' "$label" >&2
    fi
    index=$((index + 1))
  done
}

selected_key() {
  printf '%s\n' "$options" | sed -n "${selected}p" | cut -d'|' -f1
}

# Falls back to a typed answer rather than failing. A terminal that will not enter raw mode, or a
# `stty` that is not there, must not stop the question being asked — the point is the decision, and
# the arrow keys are how it is comfortable rather than how it is possible.
choose_typed() {
  printf 'choice for this session [i/%sn]: ' "${pinned:+x/}" >&2
  if IFS= read -r answer; then
    normalize "$answer"
  else
    echo ""
  fi
}

choose_with_keys() {
  saved=$(stty -g 2>/dev/null) || return 1
  stty raw -echo 2>/dev/null || return 1
  # Restored however this ends, including an interrupt. A terminal left in raw mode is a broken
  # shell, which is a worse outcome than any answer to this question.
  trap 'stty "$saved" 2>/dev/null; exit 130' INT TERM

  selected=1
  draw_options
  printf '\033[2m  up/down or j/k to move, enter to choose\033[0m' >&2

  while :; do
    key=$(read_key)
    case $key in
      up) [ "$selected" -gt 1 ] && selected=$((selected - 1)) ;;
      down) [ "$selected" -lt "$option_count" ] && selected=$((selected + 1)) ;;
      enter) break ;;
      quit) selected=0; break ;;
      *) ;;
    esac
    # Back to the top of the list, then redraw it. The hint line is one row below the options, so it
    # is cleared and rewritten with them.
    printf '\r\033[%dA' "$option_count" >&2
    draw_options
    printf '\033[K\033[2m  up/down or j/k to move, enter to choose\033[0m' >&2
  done

  stty "$saved" 2>/dev/null
  trap - INT TERM
  printf '\n' >&2
  [ "$selected" = "0" ] && return 1
  selected_key
}

# Asked only when a person can answer. `set -eu` would abort on a read at end-of-input, and a script
# blocked on a prompt is worse than one that refuses.
if [ -z "$choice" ] && [ -t 0 ] && [ -t 2 ]; then
  echo "no installed nostdb supports $contract $required." >&2
  echo >&2
  if picked=$(choose_with_keys); then
    choice=$(normalize "$picked")
  else
    choice=$(choose_typed)
  fi
  # An unreadable answer is not remembered. Storing a guess would make the rest of the session act on
  # something nobody chose, and this way the question is simply asked again.
  if [ -n "$choice" ]; then
    remember "$choice"
  fi
fi

case $choice in
  npx)
    # Unpinned unless the caller passed a version, which is the no-install route asked for.
    #
    # This is the weaker half of the trade and worth being plain about: npx runs on *every* action, so
    # with no pin the command that ran last week and the command that runs tonight can be different
    # programs, and the output is the only evidence. What keeps it honest is that it is never a
    # default — with no choice this resolves nothing — and the compatibility check asks whatever
    # arrives what contract versions it supports before an action uses it.
    echo "npx --yes --package=nostdb${pinned:+@$pinned} nostdb"
    exit 0
    ;;

  install)
    # Unpinned unless the caller passed a version, and that does not breach the product contract.
    #
    # What the contract forbids is an unpinned *fallback*: "no unpinned `latest` fallback for a
    # state-changing non-interactive action". A fallback is what happens when nobody chose, and with
    # no choice this still resolves nothing and exits 1. Installing happens because somebody picked
    # it from a list, which is the opposite of a fallback.
    #
    # The repeatedly-executed path keeps its pin. npx runs on every action, which is where "the
    # command that ran last week and the command that runs tonight are different programs" actually
    # bites, and it is what the repository verifier checks for.
    if ! command -v npm >/dev/null 2>&1; then
      echo "npm is not on the path, so this cannot install nostdb" >&2
      install_commands
      exit 1
    fi
    # Echoed before it runs. Installing software is a visible act even when it was agreed to once.
    target="nostdb${pinned:+@$pinned}"
    echo "installing $target globally, as chosen for this session" >&2
    echo "  npm install --global $target" >&2
    if ! npm install --global "$target" >&2; then
      echo "the install failed; nothing was resolved" >&2
      exit 1
    fi
    # Re-probed rather than assumed. An install that reported success and left nothing usable is
    # exactly the case a caller must not be told is fine.
    if found=$(resolve_installed); then
      echo "$found"
      exit 0
    fi
    # An install that reported success and left something that does not answer for this contract is
    # the case a caller must not be told is fine. With no pin that is the newest release genuinely
    # not supporting what was asked for, which is worth saying plainly rather than as a version.
    echo "$target installed and still does not support $contract $required" >&2
    exit 1
    ;;

  none)
    echo "continuing with no Engine, as chosen for this session" >&2
    echo "actions that need one will report what they could not do" >&2
    exit 3
    ;;
esac

# What a caller with no terminal gets, which is the normal case: an agent runs this.
#
# A marker line rather than prose, because the caller acting on it is a program deciding what to ask
# a person. The tokens are the ones NOSTDB_SKILL_ENGINE_CHOICE takes, so what is read here can be
# passed straight back.
echo "no nostdb supporting $contract $required was found" >&2
echo "decision required: install | npx | none" >&2
echo "  install  npm install --global nostdb${pinned:+@$pinned}" >&2
echo "  npx      npx --yes --package=nostdb${pinned:+@$pinned} nostdb   # installs nothing" >&2
echo "  none     resolve nothing, and report what needed an Engine" >&2
echo >&2
echo "set NOSTDB_SKILL_ENGINE_CHOICE to install, npx, or none and run this again." >&2
echo "the answer is stored for this session, so ask once and later calls need nothing." >&2
exit 1
