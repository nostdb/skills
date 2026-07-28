# Resolving the Engine

A Skill runs no database behavior of its own. Every action that touches a database invokes
the `nostdb` command, which means the first thing a Skill does is decide *which* `nostdb`.

## The order

1. **a project-local executable**, including `node_modules/.bin/nostdb`;
2. **a compatible global executable**, from an npm, Homebrew, or GitHub installation;
3. **a pinned, no-permanent-install execution**:

```bash
npx --yes --package=nostdb@<compatible-version> nostdb ...
```

Project-local first, because a project that pinned a version did so on purpose. A global
installation that overrode it would mean two people with the same checkout getting different
answers from the same command, which is the failure the pin exists to prevent.

## Never an unpinned fallback

`npx --package=nostdb` without a version is forbidden for any state-changing
non-interactive action.

A version resolved at run time is a version nobody reviewed. In an interactive session that
is merely surprising; in a script it means the command that ran last week and the command
that runs tonight are different programs, and the only evidence of the change is that the
output differs.

## Compatibility is asked, not assumed

A resolved command is verified before use:

```bash
nostdb --version --json
```

The reply names the product, the Engine version, and every contract version the build
supports — each independently, because a `.nost` language version and a `.nostdb` format
version move separately and a single product number could not express that.

A Skill checks the **contract** versions it needs, not the Engine version. An Engine two
releases newer that still reads `nost_language_version` 2 is compatible; one that dropped it
is not, however close the version numbers look.

A command that does not answer `--version --json` is not treated as an old `nostdb`. It is
treated as not being `nostdb` at all, because something on the path with the right name and
the wrong behavior is more dangerous than nothing on the path.

## What resolution does not do

It does not install anything. If no compatible Engine is found, the Skill reports the exact
commands that would install one and stops — a Skill that installed software because it
needed some is a Skill nobody can safely run in a directory they do not own.

It does not fall back to drafting. A Skill can write a candidate `.nost` with no Engine at
all, and that is a real capability, but it is not a substitute for a build: a draft is not a
valid `.nostdb`, and reporting one as though it were would be reporting a success that did
not happen.
