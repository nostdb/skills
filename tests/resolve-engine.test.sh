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

PATH="/usr/bin:/bin" "$resolve" nost_language_versions 2 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "nothing installed is a refusal, not a guess" "$r" "refused"

fake "$work/global/nostdb" "$supports"
got=$(PATH="$work/global:/usr/bin:/bin" "$resolve" nost_language_versions 2)
check "a compatible global is used" "$got" "$work/global/nostdb"

# A project that pinned a version did so on purpose.
fake "$work/node_modules/.bin/nostdb" "$supports"
got=$(PATH="$work/global:/usr/bin:/bin" "$resolve" nost_language_versions 2)
check "project-local beats a global" "$got" "./node_modules/.bin/nostdb"

fake "$work/node_modules/.bin/nostdb" "$other"
got=$(PATH="$work/global:/usr/bin:/bin" "$resolve" nost_language_versions 2)
check "an incompatible local falls through" "$got" "$work/global/nostdb"

# The same two candidates, asked about a contract they both support: the local one wins
# again. Together with the check above — where the local did not support what was asked and
# was passed over — this is what "compatibility is per contract" means. One resolution order
# does not decide every question; each contract is asked separately.
got=$(PATH="$work/global:/usr/bin:/bin" "$resolve" settings_versions 1)
check "a contract both support resolves to the local one" "$got" "./node_modules/.bin/nostdb"

# Something with the right name and the wrong behavior is worse than nothing.
rm -rf "$work/node_modules"
printf '#!/bin/sh\nexit 0\n' > "$work/impostor_nostdb"
mkdir -p "$work/impostor" && mv "$work/impostor_nostdb" "$work/impostor/nostdb"
chmod +x "$work/impostor/nostdb"
PATH="$work/impostor:/usr/bin:/bin" "$resolve" nost_language_versions 2 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "a command that does not answer is refused" "$r" "refused"

fake "$work/twelve/nostdb" 'echo "{\"nost_language_versions\":[12]}"'
PATH="$work/twelve:/usr/bin:/bin" "$resolve" nost_language_versions 1 >/dev/null 2>&1 \
  && r=resolved || r=refused
check "supporting 12 is not supporting 1" "$r" "refused"

if grep -qE 'package=nostdb[^@]' "$resolve"; then
  echo "FAIL an unpinned npx fallback is present" >&2
  failures=$((failures + 1))
else
  echo "ok   no unpinned fallback exists"
fi

[ "$failures" -eq 0 ] || { echo "$failures check(s) failed" >&2; exit 1; }
echo "resolution: every check passed"
