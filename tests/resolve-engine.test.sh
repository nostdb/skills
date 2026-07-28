#!/bin/sh
# Proves the resolution order against fake engines.
#
# No real nostdb is installed here and none is needed: what is under test is the order and
# the compatibility check, both of which a fake answers exactly as a real one would. It is
# also the only way to test the case where nothing compatible exists, which a machine with a
# working installation cannot produce.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
resolve="$here/../skills/nostdb/scripts/resolve-engine.sh"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

failures=0
check() {
  if [ "$2" = "$3" ]; then
    echo "ok   $1"
  else
    echo "FAIL $1: expected [$3], got [$2]" >&2
    failures=$((failures + 1))
  fi
}

fake() {
  mkdir -p "$(dirname "$1")"
  printf '#!/bin/sh\n[ "$1" = "--version" ] || exit 3\n%s\n' "$2" > "$1"
  chmod +x "$1"
}

supports='echo "{\"product\":\"nostdb\",\"nost_language_versions\":[2],\"settings_versions\":[1]}"'
other='echo "{\"product\":\"nostdb\",\"nost_language_versions\":[3],\"settings_versions\":[1]}"'
cd "$work"

# Every case below runs non-interactively, so the decision comes from the environment or the
# remembered file and never from a prompt. That is also the guarantee under test for a script: a
# resolution that blocked on a question nobody could answer would hang a caller.
state="$work/remembered"
export NOSTDB_SKILL_STATE="$state"

PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "nothing installed is a refusal, not a guess" "$r" "refused"

# A pinned version used to make npx the automatic answer, so every action paid its cost without
# anyone choosing it. Passing one must no longer resolve anything on its own.
PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 1.4.0 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "a pinned version alone no longer resolves to npx" "$r" "refused"

fake "$work/global/nostdb" "$supports"
got=$(PATH="$work/global:/usr/bin:/bin" "$resolve" nost_language_version 2)
check "a compatible global is used" "$got" "$work/global/nostdb"

# A project that pinned a version did so on purpose.
fake "$work/node_modules/.bin/nostdb" "$supports"
got=$(PATH="$work/global:/usr/bin:/bin" "$resolve" nost_language_version 2)
check "project-local beats a global" "$got" "./node_modules/.bin/nostdb"

fake "$work/node_modules/.bin/nostdb" "$other"
got=$(PATH="$work/global:/usr/bin:/bin" "$resolve" nost_language_version 2)
check "an incompatible local falls through" "$got" "$work/global/nostdb"

# The same two candidates, asked about a contract they both support: the local one wins
# again. Together with the check above — where the local did not support what was asked and
# was passed over — this is what "compatibility is per contract" means. One resolution order
# does not decide every question; each contract is asked separately.
got=$(PATH="$work/global:/usr/bin:/bin" "$resolve" settings_version 1)
check "a contract both support resolves to the local one" "$got" "./node_modules/.bin/nostdb"

# Something with the right name and the wrong behavior is worse than nothing.
rm -rf "$work/node_modules"
printf '#!/bin/sh\nexit 0\n' > "$work/impostor_nostdb"
mkdir -p "$work/impostor" && mv "$work/impostor_nostdb" "$work/impostor/nostdb"
chmod +x "$work/impostor/nostdb"
PATH="$work/impostor:/usr/bin:/bin" "$resolve" nost_language_version 2 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "a command that does not answer is refused" "$r" "refused"

# The decision, in each of the three ways it can arrive.
rm -rf "$work/node_modules" "$state"
got=$(PATH="/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=x "$resolve" nost_language_version 2 1.4.0)
check "a pin the caller passed is used for npx" "$got" "npx --yes --package=nostdb@1.4.0 nostdb"

# The no-install route, which is what a Skill uses: no version named, so npx takes the newest.
got=$(PATH="/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=x "$resolve" nost_language_version 2)
check "no install runs the newest through npx" "$got" "npx --yes --package=nostdb nostdb"

# Captured rather than tested directly: this file runs under `set -e`, so a bare command exiting 3
# would end the suite before the check that wants to see the 3.
PATH="/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=n "$resolve" nost_language_version 2 >/dev/null 2>&1 \
  && code=0 || code=$?
check "choosing to continue without an Engine exits 3" "$code" "3"

# Installing with no pin asks npm for the newest release, and the command it runs is checked without
# letting anything reach this machine: a fake npm records the arguments and fails, so the shape is
# proven and nothing is installed. A test that really installed software would be a test nobody could
# run twice.
mkdir -p "$work/fakenpm"
cat > "$work/fakenpm/npm" <<'FAKE'
#!/bin/sh
echo "$@" > "$FAKE_NPM_LOG"
exit 1
FAKE
chmod +x "$work/fakenpm/npm"

FAKE_NPM_LOG="$work/npm.args" \
  PATH="$work/fakenpm:/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=i \
  "$resolve" nost_language_version 2 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "an install that fails resolves nothing" "$r" "refused"
check "installing with no pin asks for the newest release" \
  "$(cat "$work/npm.args" 2>/dev/null)" "install --global nostdb"

# A caller that does pass one is still honored: the skill not naming a version is not the same as
# refusing one it was handed.
FAKE_NPM_LOG="$work/npm.pinned" \
  PATH="$work/fakenpm:/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=i \
  "$resolve" nost_language_version 2 1.4.0 >/dev/null 2>&1 || true
check "a pin the caller passed is used for the install" \
  "$(cat "$work/npm.pinned" 2>/dev/null)" "install --global nostdb@1.4.0"

# The path an agent actually takes: no terminal, so the answer arrives in the environment once and
# every later call is expected to need nothing. This is what makes it once per *session* rather than
# once per call, and it was not true until the environment-stated answer was stored as well as used.
rm -f "$state"
got=$(PATH="/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=npx "$resolve" nost_language_version 2 </dev/null)
check "an answer stated without a terminal resolves" "$got" "npx --yes --package=nostdb nostdb"
check "and is stored, so the session is not asked again" "$(cat "$state" 2>/dev/null)" "npx"
got=$(PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 </dev/null)
check "a later call needs no environment at all" "$got" "npx --yes --package=nostdb nostdb"

# The refusal has to tell a caller what to ask, in the tokens the variable takes.
rm -f "$state"
PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 </dev/null 2>"$work/ask.err" || true
check "the refusal names the decision it needs" \
  "$(grep -c 'decision required: install | npx | none' "$work/ask.err")" "1"

# A remembered decision is honored with nothing in the environment, which is the whole point of
# remembering it.
printf 'none\n' > "$state"
PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 >/dev/null 2>&1 \
  && code=0 || code=$?
check "a remembered decision needs no environment" "$code" "3"

printf 'x\n' > "$state"
got=$(PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 1.4.0)
check "a stored short spelling means the same as the long one" "$got" "npx --yes --package=nostdb@1.4.0 nostdb"

# Windows: there is nothing to offer, because nothing in the product builds there. A fake uname is
# how that is reachable from a machine that is not Windows, and the alternative is a branch nobody
# ever runs.
rm -f "$state"
mkdir -p "$work/win"
printf '#!/bin/sh\necho MINGW64_NT-10.0\n' > "$work/win/uname"
chmod +x "$work/win/uname"
PATH="$work/win:/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=x "$resolve" nost_language_version 2 \
  >/dev/null 2>"$work/win.err" && r=resolved || r=refused
check "Windows is refused rather than offered an install" "$r" "refused"
check "the refusal says why, not just that it failed" \
  "$(grep -c 'no Windows build' "$work/win.err")" "1"
check "the refusal points at WSL" "$(grep -c 'WSL' "$work/win.err")" "1"

# A decision nobody made must not be invented from an unreadable file.
printf 'maybe\n' > "$state"
PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 1.4.0 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "an unreadable stored decision resolves nothing" "$r" "refused"

# An installed Engine is used without consulting the decision at all, so a remembered "none" cannot
# strand a caller that has one.
printf 'none\n' > "$state"
fake "$work/global/nostdb" "$supports"
got=$(PATH="$work/global:/usr/bin:/bin" "$resolve" nost_language_version 2)
check "an installed Engine outranks a remembered decision" "$got" "$work/global/nostdb"
rm -f "$state"
rm -rf "$work/global"

# The arrow-key list, driven through a pseudo-terminal.
#
# Everything above runs with no terminal, which is how a script runs it and is also why none of it
# reaches the menu. The menu is the part a person actually uses, so it is driven here for real:
# without a pty there is no raw mode, no escape sequences, and nothing to test.
#
# Skipped where python3 is absent rather than made a dependency of the suite. Every other check here
# is `/bin/sh`, and the one that needs more says so.
if command -v python3 >/dev/null 2>&1; then
  rm -f "$state"
  driver="$work/drive.py"
  cat > "$driver" <<'PYTHON'
import os, pty, select, sys, time

script, state, keys = sys.argv[1], sys.argv[2], sys.argv[3]
env = dict(os.environ, NOSTDB_SKILL_STATE=state, PATH="/usr/bin:/bin")
pid, fd = pty.fork()
if pid == 0:
    os.execvpe("/bin/sh", ["/bin/sh", script, "nost_language_version", "2", "1.4.0"], env)

out = b""
def drain(seconds):
    global out
    end = time.time() + seconds
    while time.time() < end:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if ready:
            try:
                out += os.read(fd, 4096)
            except OSError:
                return
drain(0.6)
for key in keys:
    os.write(fd, b"\x1b[B" if key == "d" else b"\r")
    drain(0.25)
drain(0.6)
code = os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1])
sys.stdout.write(out.decode("utf-8", "replace"))
sys.stderr.write(str(code))
PYTHON

  # Down once selects the second option, npx, and enter takes it.
  code=$(python3 "$driver" "$resolve" "$state" "dr" 2>&1 >"$work/tui.out" || true)
  check "the menu resolves what enter selected" \
    "$(grep -c 'npx --yes --package=nostdb@1.4.0 nostdb' "$work/tui.out")" "1"
  check "the menu remembers what was selected" "$(cat "$state" 2>/dev/null)" "npx"

  # The marker has to move, or the arrow keys did nothing and the first option was taken by default.
  check "down moved the selection off the first option" \
    "$(grep -c '\[x\] Do not install' "$work/tui.out")" "1"

  # The same session is not asked twice.
  python3 "$driver" "$resolve" "$state" "" >"$work/tui2.out" 2>/dev/null || true
  check "a second run in one session is not asked again" \
    "$(grep -c 'up/down or j/k' "$work/tui2.out")" "0"
  rm -f "$state"
else
  echo "skip python3 is absent; the arrow-key menu was not driven"
fi

fake "$work/twelve/nostdb" 'echo "{\"nost_language_versions\":[12]}"'
PATH="$work/twelve:/usr/bin:/bin" "$resolve" nost_language_version 1 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "supporting 12 is not supporting 1" "$r" "refused"

# The fakes answer the shape a real Engine answers, checked against one when there is one.
#
# This is the gap the budget suite found in Stage 10, in this same repository: a fixture whose author
# also wrote the thing it tests agrees with the author's idea of the document. Here the fakes emitted
# the *contract* key and the script asked for the contract key, so both agreed — and a real report,
# which answers with the key plus an `s`, matched neither.
if command -v nostdb >/dev/null 2>&1; then
  real=$(nostdb --version --json 2>/dev/null || true)
  case "$real" in
    *'"nost_language_versions"'*)
      echo "ok   a real Engine answers the key the fakes answer" ;;
    *)
      echo "FAIL a real nostdb reports something these fakes do not: $real" >&2
      failures=$((failures + 1)) ;;
  esac
  # And the script can actually read it, which is the whole question.
  if nostdb --version --json 2>/dev/null | grep -q '"nost_language_versions"'; then
    got=$(PATH="$(dirname "$(command -v nostdb)"):/usr/bin:/bin" "$resolve" nost_language_version 2 2>/dev/null || echo REFUSED)
    case "$got" in
      REFUSED) echo "FAIL a real Engine on the path was refused" >&2; failures=$((failures + 1)) ;;
      *) echo "ok   a real Engine on the path resolves" ;;
    esac
  fi
else
  echo "skip no nostdb on the path; the real-report check did not run"
fi

# The unpinned npx form is present on purpose now, and what is checked is that it is not a *fallback*.
# Both cases above establish it — nothing installed and no choice resolves nothing, with or without a
# pinned version passed — so this asserts the property directly rather than banning the string.
rm -f "$state"
if PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 >/dev/null 2>&1; then
  echo "FAIL an unpinned npx is reachable without a choice" >&2
  failures=$((failures + 1))
elif PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 1.4.0 >/dev/null 2>&1; then
  echo "FAIL passing a version alone reaches npx without a choice" >&2
  failures=$((failures + 1))
else
  echo "ok   npx is a choice and never a fallback"
fi

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "resolution: every check passed"
