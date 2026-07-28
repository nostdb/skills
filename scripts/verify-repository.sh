#!/bin/sh
# Independent verification for skills.
#
# This repository holds no compiled code, so the checks are about the boundaries a Skill must
# not cross rather than about a build. They run now, before there are actions to break them.
set -eu
cd "$(dirname "$0")/.."

# SKILL.md is deliberately not in this list. Which documents this Skill publishes is specific
# to it and belongs here; whether a definition exists and is discoverable is a property of
# every skill, and the layout checks below own it — naming one path here as well would make
# their diagnostic unreachable and leave the general rule unproven.
for required in README.md AGENTS.md CLAUDE.md LICENSE \
    skills/nostdb/ACTIONS.md skills/nostdb/RESOLUTION.md skills/nostdb/ENRICHMENT.md; do
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

# A Skill is installable only if an installer can find it and the folder it copies is
# complete. Both are checked here, because "independently installable" is a claim this
# repository makes in its own README and nothing verified it: until now it shipped an action
# table, four scripts, and no SKILL.md at all.
#
# An installer scans `skills/<name>/SKILL.md` and `skills/<category>/<name>/SKILL.md`, and
# copies the whole skill folder. Anything a definition references from outside that folder is
# absent once installed.
#
# Depth is part of the contract, so the two layouts are written as a pattern rather than as a
# search that would accept any depth: a definition one level deeper is a file this repository
# contains and no installer offers.
discovered='^skills/[^/]+/SKILL\.md$|^skills/[^/]+/[^/]+/SKILL\.md$'
found=$(find . -name SKILL.md -not -path './.git/*' 2>/dev/null | sed 's|^\./||' | LC_ALL=C sort)
definitions=$(printf '%s\n' "$found" | grep -E "$discovered" || true)
if [ -z "$definitions" ]; then
  echo "no installable skill found; an installer discovers skills/<name>/SKILL.md" >&2
  exit 1
fi

# Anywhere else is a definition nobody can ask for: outside `skills/`, too shallow, or too
# deep. This also catches one left behind by a move.
if undiscoverable=$(printf '%s\n' "$found" | grep -vE "$discovered" | grep .); then
  echo "these definitions are at a path no installer discovers:" >&2
  printf '%s\n' "$undiscoverable" >&2
  exit 1
fi

for definition in $definitions; do
  folder=$(dirname "$definition")
  name=$(basename "$folder")

  # Frontmatter, and it has to come first: a definition whose opening delimiter is not on
  # line 1 is read as prose, so the skill installs and then never triggers.
  if [ "$(head -1 "$definition")" != "---" ]; then
    echo "$definition must open with a --- frontmatter delimiter on line 1" >&2
    exit 1
  fi

  closing=$(awk 'NR > 1 && $0 == "---" { print NR; exit }' "$definition")
  if [ -z "$closing" ]; then
    echo "$definition has no closing --- frontmatter delimiter" >&2
    exit 1
  fi
  frontmatter=$(sed -n "2,$((closing - 1))p" "$definition")

  # `name` and `description` are what an agent selects a skill by. A definition with no
  # description never triggers, however good its body is.
  for field in name description; do
    if ! printf '%s\n' "$frontmatter" | grep -q "^$field: *[^ ]"; then
      echo "$definition declares no $field in its frontmatter" >&2
      exit 1
    fi
  done

  declared=$(printf '%s\n' "$frontmatter" | sed -n 's/^name: *//p' | head -1)
  if [ "$declared" != "$name" ]; then
    echo "$definition declares the name $declared and sits in $name; the two must agree" >&2
    exit 1
  fi

  # Every reference a definition makes must resolve inside its own folder, because the folder
  # is the unit that gets copied. Two extractions, both unambiguous: a Markdown link target,
  # and a `scripts/<name>.sh` invocation. A looser path-shaped scan would fire on
  # `.nostdb/root.nost`, which is a path in a user's project rather than a file in this one.
  references=$(
    {
      grep -oE '\]\([^)#][^)]*\)' "$definition" | sed 's/^](//; s/)$//'
      grep -oE 'scripts/[A-Za-z0-9_-]+\.sh' "$definition"
    } | grep -v '://' | LC_ALL=C sort -u
  )
  for reference in $references; do
    if [ ! -e "$folder/$reference" ]; then
      echo "$definition references $reference, which is not in the folder an installer copies" >&2
      exit 1
    fi
  done

  # A script a definition invokes has to be executable here. Nothing that copies the folder
  # will add the bit afterwards.
  for script in $(find "$folder" -name '*.sh'); do
    if [ ! -x "$script" ]; then
      echo "$script is not executable, so an installed skill could not run it" >&2
      exit 1
    fi
  done

  echo "installable: $folder"
done

# Only the Engine writes .nostdb. A Skill that shipped a writer would be a second one.
if grep -rn --include='*.md' --include='*.json' --include='*.sh' \
    -E '\b(commit_graph|write_database|ContainerBuilder)\b' . 2>/dev/null | grep -v '^\./scripts/' | grep -v '^\./tests/'; then
  echo "only the Engine writes .nostdb; a Skill proposes changes and never commits them" >&2
  exit 1
fi

# The root contract forbids an unpinned `latest` **fallback** for a state-changing non-interactive
# action. This used to be read as forbidding the unpinned npx form outright, and that is no longer
# what is enforced: the no-install route runs `npx --yes --package=nostdb nostdb`, unpinned, because
# a Skill naming an Engine version is a version that goes stale in a document nobody re-reads.
#
# What still holds is the word "fallback". The unpinned form is reachable only after somebody chose
# it; with no choice, resolution resolves nothing and exits 1. So what is checked is that the form
# appears in exactly one place — the resolver that emits it after a decision — and nowhere else,
# because an unpinned npx sprinkled into another script or a skill definition would be a default
# again, and nothing would have decided it.
#
# `tests/resolve-engine.test.sh` is where "no choice resolves nothing" is actually proven, and the
# check below requires that case to exist rather than trusting this comment.
#
# Scripts and skill definitions only. An earlier version also searched markdown and fired on the
# document that *states* the prohibition — the same mistake the provider's verifier made about
# `.nostdb` paths. A document explaining a rule has to be able to write the rule down, and a check
# that forbids that is one people learn to work around.
if grep -rn --include='*.json' --include='*.sh' -E 'package=nostdb[^@]' . 2>/dev/null \
    | grep -v '^\./scripts/verify-repository.sh' \
    | grep -v '^\./tests/resolve-engine.test.sh' \
    | grep -v '^\./skills/nostdb/scripts/resolve-engine\.sh'; then
  echo "the unpinned npx form belongs only in the resolver that emits it after a choice" >&2
  echo "anywhere else it is a default again, and nothing decided it" >&2
  exit 1
fi

# The guarantee the exclusion above rests on: with nothing chosen, nothing resolves.
if ! grep -q 'a pinned version alone no longer resolves to npx' tests/resolve-engine.test.sh \
  || ! grep -q 'nothing installed is a refusal, not a guess' tests/resolve-engine.test.sh; then
  echo "the suite must prove that no choice resolves nothing; that is what permits an unpinned npx" >&2
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

if [ -x tests/dispatch.test.sh ]; then
  tests/dispatch.test.sh >/dev/null || {
    echo "the dispatch tests failed" >&2
    tests/dispatch.test.sh >&2
    exit 1
  }
  echo "dispatch: every check passed"
fi

if [ -x tests/budget-check.test.sh ]; then
  tests/budget-check.test.sh >/dev/null || {
    echo "the budget check tests failed" >&2
    tests/budget-check.test.sh >&2
    exit 1
  }
  echo "budget: every check passed"
fi

if [ -x tests/nl-gate.test.sh ]; then
  tests/nl-gate.test.sh >/dev/null || {
    echo "the natural-language gate tests failed" >&2
    tests/nl-gate.test.sh >&2
    exit 1
  }
  echo "natural language: every check passed"
fi

echo "skills verification passed"
