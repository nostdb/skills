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
| install | `npm install --global nostdb` runs, then resolution is **re-probed** rather than assumed |
| npx | `npx --yes --package=nostdb nostdb` is printed, installing nothing |
| none | exit `3`, offered only through the environment, for a caller that wants nothing touched |

Neither names a version. A Skill names the contract it needs, not an Engine version: a version baked
into a definition goes stale in a document nobody re-reads, and the compatibility check below is what
decides whether what arrived is usable. A caller that passes one is still honored.

The npx route is the weaker half of the trade, and it is worth being plain about. npx runs on
**every** action, so with no pin the command that ran last week and the command that runs tonight can
be different programs, with the output as the only evidence. What keeps it honest is that it is never
a default, and that whatever arrives is asked what it supports before an action uses it.

## Unpinned, but never a fallback

The rule below forbids an unpinned `latest` **fallback** for a state-changing non-interactive action,
and the load-bearing word is *fallback*: what happens when nobody chose.

With no choice, resolution resolves nothing and exits `1`. That holds whether or not a version was
passed, and the suite proves both — which is what the repository verifier requires before it permits
the unpinned form to exist at all. The verifier also requires that form to appear in exactly one
place, the resolver that emits it after a decision, because an unpinned npx copied into another
script would be a default again and nothing would have decided it.

## Windows

There is nothing to resolve. NostDB publishes four targets, all macOS and Linux, and Windows is
recorded as intended and not buildable: `nostdb-server` implements only the Unix domain socket while
the protocol contract specifies a named pipe there, so nothing in the product compiles for Windows.

A shell reporting `MINGW`, `MSYS`, or `CYGWIN` is a POSIX layer on Windows — the only way these
scripts run there at all — and resolution refuses with that reason rather than offering an install
that would download nothing usable. WSL reports Linux and is a published target, so it is not caught.

These scripts are `/bin/sh` and need a POSIX shell regardless. That is the smaller of the two
constraints: a Windows user who supplies one still has no Engine to run.

## Who asks

Whoever has a terminal. That is usually **not** this script.

A Skill is normally run by an agent, which invokes it with no controlling terminal, so the menu below
is unreachable in the common case. Resolution therefore exits `1` with a marker line —
`decision required: install | npx | none` — and the caller asks the person and states the answer in
`NOSTDB_SKILL_ENGINE_CHOICE`. The tokens in the marker are exactly the ones the variable takes, so
what was read can be passed straight back.

An answer that arrives that way is **stored**, not just honored. Otherwise "once per session" would
describe only the prompt, and the prompt is the path nobody takes: a caller would have to repeat the
answer on every call, which is a question asked once and answered forever after by hand.

The menu below is for a person running this directly.

## Asked with a list, once per session

The question is a list the arrow keys move through, `j` and `k` too, and enter takes the marked line:

```text
  [ ] Install nostdb@1.4.0 globally
  [x] Run it with a pinned npx each time, installing nothing
  [ ] Continue without an Engine, and report what needs one
  up/down or j/k to move, enter to choose
```

It is drawn on standard error. Standard output carries the resolved command and nothing else, so a
caller can use it directly, and a menu printed there would become the command.

A terminal that will not enter raw mode falls back to a typed answer rather than failing. The arrow
keys are how the question is comfortable, not how it is possible. The terminal is restored however
the prompt ends, including an interrupt: a shell left in raw mode is a worse outcome than any answer.

## The decision is remembered for a session, and the resolution is not remembered at all

The answer is stored as one line under the temporary directory, keyed by the POSIX session — what
"session" means, and what every process in one terminal shares. Where there is no controlling
terminal the parent shell stands in, so repeated calls from one shell agree and a new shell asks
again. `NOSTDB_SKILL_STATE` overrides the path and `NOSTDB_SKILL_ENGINE_CHOICE` states the answer
without a prompt.

A session, rather than for ever, because this is a question about right now. Somebody who chose "no
Engine" to get through one afternoon should not still be living with it next week, and the temporary
directory means the operating system clears the file instead of a home directory accumulating one per
session.

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
