# Resolving the Engine

A Skill runs no database behavior of its own. Every action that touches a database invokes
the `nostdb` command, which means the first thing a Skill does is decide *which* `nostdb`.

## The order

1. **a project-local executable**, including `node_modules/.bin/nostdb`;
2. **a compatible global executable**, from an npm, Homebrew, or GitHub installation.

Project-local first, because a project that pinned a version did so on purpose. A global
installation that overrode it would mean two people with the same checkout getting different
answers from the same command, which is the failure the pin exists to prevent.

An installed Engine costs one process: the first candidate that exists is asked, and resolution
stops there.

## npx is a choice, not a third step

It was a third step, and that was the mistake. Passing a pinned version made

```bash
npx --yes --package=nostdb@<version> nostdb ...
```

the automatic answer whenever nothing was installed. Resolution itself was quick; the command it
handed back was not, so every action paid a fetch and a Node start-up that nobody had agreed to.

With nothing installed there are three answers, and which one applies is a decision rather than an
order:

| Choice | What happens |
| --- | --- |
| install | a pinned global install runs, then resolution is **re-probed** rather than assumed |
| npx | the pinned `npx` form is printed, paying its cost knowingly |
| none | exit `3`, and the caller reports what it could not do |

Each needs a pinned version except `none`. Consent to install a reviewed version is not consent to
whatever is newest, which is the same rule as the section below and the reason it is not relaxed
just because somebody said yes once.

## The decision is remembered, the resolution is not

The answer is stored in `~/.nostdb/skill-engine`, overridable with `NOSTDB_SKILL_STATE`, as one
line. `NOSTDB_SKILL_ENGINE_CHOICE` states it without a prompt.

What is stored is the decision a person made, not the command it resolved to. A cached path would be
a lie the moment the Engine was installed, upgraded, or removed, and re-probing costs one process —
so the slow thing is cached and the thing that goes stale is not.

An installed Engine is used **without consulting the decision at all**, so a remembered "none"
cannot strand a caller who has since installed one.

A prompt happens only when both standard input and standard error are terminals. A script is never
asked and never installs anything on its own: it exits `1` with the exact commands.

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

Ask by the contract key, which is what the version registry publishes and what every document
names. The report answers with what the build *supports*, which is a list, so its key is the
contract key plus an `s`:

```bash
scripts/resolve-engine.sh nost_language_version 2   # asks; the report answers
                                                    # "nost_language_versions": [2]
```

That relationship is written down because getting it wrong is invisible: asking for the singular
key finds nothing in a real report, and a working Engine is reported incompatible. Every fake in
this repository's own suite answered the singular key, so the fakes agreed with the question and
neither agreed with the Engine — which is why the suite now checks a real report when one is on
the path.

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
