#!/bin/sh
# Independent verification for skills.
#
# This repository holds no compiled code, so the checks are about the boundaries a Skill must
# not cross rather than about a build. They run now, before there are actions to break them.
set -eu
cd "$(dirname "$0")/.."

for required in README.md AGENTS.md CLAUDE.md LICENSE nostdb/ACTIONS.md; do
  if [ ! -e "$required" ]; then
    echo "missing required file: $required" >&2
    exit 1
  fi
done

if [ ! -L CLAUDE.md ] || [ "$(readlink CLAUDE.md)" != "AGENTS.md" ]; then
  echo "CLAUDE.md must be a symlink to AGENTS.md" >&2
  exit 1
fi

if ! grep -q '^ *Apache License$' LICENSE; then
  echo "LICENSE must be the Apache License" >&2
  exit 1
fi

# Only the Engine writes .nostdb. A Skill that shipped a writer would be a second one.
if grep -rn --include='*.md' --include='*.json' --include='*.sh' \
    -E '\b(commit_graph|write_database|ContainerBuilder)\b' . 2>/dev/null | grep -v '^\./scripts/' | grep -v '^\./tests/'; then
  echo "only the Engine writes .nostdb; a Skill proposes changes and never commits them" >&2
  exit 1
fi

# The root contract forbids an unpinned fallback for a state-changing non-interactive
# action. A version resolved at run time is a version nobody reviewed.
#
# Scripts and skill definitions only. An earlier version also searched markdown and fired on
# the document that *states* the prohibition — the same mistake the provider's verifier made
# about `.nostdb` paths. A document explaining a rule has to be able to write the rule down,
# and a check that forbids that is one people learn to work around.
if grep -rn --include='*.json' --include='*.sh' -E 'package=nostdb[^@]' . 2>/dev/null \
    | grep -v '^\./scripts/verify-repository.sh' \
    | grep -v '^\./tests/resolve-engine.test.sh'; then
  echo "an unpinned latest fallback is forbidden for a state-changing action" >&2
  exit 1
fi

# A credential must never appear here. This repository holds prompts, and a prompt is the
# easiest place in the product for one to be pasted by accident.
if grep -rnE '\b(gh[pousr]_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{20,})' . 2>/dev/null | grep -v '^\./scripts/' | grep -v '^\./tests/'; then
  echo "a credential must never appear in this repository" >&2
  exit 1
fi

if [ -e docs/PRD.md ] || [ -e grammar ] || [ -e fixtures ]; then
  echo "the PRD, the grammar, and the fixtures each live once, elsewhere" >&2
  exit 1
fi

# The resolution tests run here rather than only by hand: the order they check is a
# product contract, and a check nothing runs is documentation.
if [ -x tests/resolve-engine.test.sh ]; then
  tests/resolve-engine.test.sh >/dev/null || {
    echo "the engine resolution tests failed" >&2
    tests/resolve-engine.test.sh >&2
    exit 1
  }
  echo "resolution: every check passed"
fi

echo "skills verification passed"
