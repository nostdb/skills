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
check "choosing npx resolves the pinned form" "$got" "npx --yes --package=nostdb@1.4.0 nostdb"

PATH="/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=x "$resolve" nost_language_version 2 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "choosing npx without a pin is refused, not guessed" "$r" "refused"

# Captured rather than tested directly: this file runs under `set -e`, so a bare command exiting 3
# would end the suite before the check that wants to see the 3.
PATH="/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=n "$resolve" nost_language_version 2 >/dev/null 2>&1 \
  && code=0 || code=$?
check "choosing to continue without an Engine exits 3" "$code" "3"

# Installing needs a pin for the same reason npx does: consent to a reviewed version is not consent
# to whatever is newest.
PATH="/usr/bin:/bin" NOSTDB_SKILL_ENGINE_CHOICE=i "$resolve" nost_language_version 2 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "installing without a pin is refused" "$r" "refused"

# A remembered decision is honored with nothing in the environment, which is the whole point of
# remembering it.
printf 'none\n' > "$state"
PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 >/dev/null 2>&1 \
  && code=0 || code=$?
check "a remembered decision needs no environment" "$code" "3"

printf 'x\n' > "$state"
got=$(PATH="/usr/bin:/bin" "$resolve" nost_language_version 2 1.4.0)
check "a stored short spelling means the same as the long one" "$got" "npx --yes --package=nostdb@1.4.0 nostdb"

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

if grep -qE 'package=nostdb[^@]' "$resolve"; then
  echo "FAIL an unpinned npx fallback is present" >&2
  failures=$((failures + 1))
else
  echo "ok   no unpinned fallback exists"
fi

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "resolution: every check passed"
