---
name: nostdb
description: Build, query, and synchronize a NostDB property graph of a codebase through the nostdb command surface. Use when asked to create or refresh a .nostdb, materialize the canonical .nost, run an openCypher query over a code graph, ask in natural language how parts of a codebase connect, reconcile .nost with .nostdb, open a graph viewer, or install a NostDB plugin.
license: Apache-2.0
metadata:
  version: 1
  requires:
    nost_language_version: 2
    query_subset_version: 1
---

# NostDB

The AI-capable extension of the `nostdb` command surface. Not a second database
implementation, not a competing command surface, and not a file writer.

Every action below resolves a compatible `nostdb` command and invokes it. What the Engine
returns is rendered; what it refuses is reported. Nothing here reimplements a parser, a
storage engine, a synchronizer, an analyzer, or a query engine.

## Refusals that hold before anything else

- **Never write `.nostdb`.** Only the Engine writes one. A Skill may draft a candidate
  `.nost` or propose a versioned change set, and the Engine validates ownership, generation,
  endpoints, schemas, constraints, and evidence before anything is committed.
- **Never resolve a version at run time.** A version nobody reviewed is merely surprising in
  an interactive session; in a script it means last week's command and tonight's are
  different programs, and the only evidence is that the output differs.
- **Never place a credential in a prompt, an analysis packet, a log record, a diagnostic, or
  output.** This Skill holds prompts, which is the easiest place in the product for a secret
  to be pasted by accident.
- **Never execute analyzed source code.**
- **A drafted `.nost` is not a build.** Reporting one as though it were reports a success
  that did not happen.

## Surface

This is what `/nostdb help` shows. **Show it from here.** Do not resolve an Engine and do not run
anything: `help` describes this Skill, the Skill is what knows, and asking somebody to install a
database in order to read a help message is the wrong order of operations.

```text
/nostdb .                          analyze this folder and write the database
/nostdb . --nost                   the same, and materialize the canonical .nost
/nostdb . --ai=off                 the same, with enrichment refused rather than skipped
/nostdb . --ai=full                enrichment required; fails without a model
/nostdb .nostdb/root.nost --sync   reconcile .nost and .nostdb
/nostdb query --cypher '...'       run a statement you wrote
/nostdb query "..."                ask in English; the generated Cypher is shown
/nostdb view .                     render the graph through a viewer plugin
/nostdb plugin add '...'           install a plugin from a pinned GitHub source
/nostdb help                       this
```

`/nostdb .` with no path means the current folder. It configures the project if it is not configured,
analyzes the whole tree, and writes `.nostdb/settings.json` and `.nostdb/root.nostdb`.

It does **not** write `.nost` unless the project already has it enabled or `--nost` is passed. A flag's
absence is not a request, and materialization is an explicit choice rather than a side effect of
building.

## Step 1: resolve the Engine

Do this before every action that touches a database, and pass the contract version the action
needs rather than an Engine version:

```bash
scripts/resolve-engine.sh nost_language_version 2
scripts/resolve-engine.sh query_subset_version 1
```

Pass no version. The Skill names the **contract** it needs and lets the install be the newest release
that satisfies it; a version baked into a Skill definition is a version that goes stale in a document
nobody re-reads. A third argument is still accepted, and a caller who has a reason to pin one gets the
pinned `npx` option as well.

It prints the command to use and nothing else. Exit `0` resolved, `1` nothing compatible found
and no decision, `2` used incorrectly, `3` the caller chose to continue with no Engine.

An installed Engine resolves in one process, and a pinned version no longer makes `npx` the
automatic answer. It used to: passing one meant every action paid npx's fetch and start-up cost
without anyone choosing it.

### With nothing installed, ask once for the session

Exit `1` prints `decision required: install | npx | none`. **You** ask the question, because you are
the one who can be answered — this script has no terminal when an agent runs it, so its own prompt
never appears.

**Ask it the way you ask anything else, and take a typed answer.** Do not draw a checkbox list, a
menu, or anything else that looks like a control: a reader cannot click text, and a list of `[ ]`
boxes tells somebody to do something they have no way of doing. If you have a native way to offer a
choice, use that. Otherwise ask in one sentence and name the three answers.

The three answers, and what each one means:

- **install** — `npm install --global nostdb`, and it stays installed
- **npx** — `npx --yes --package=nostdb nostdb`, installing nothing and fetching each run
- **none** — resolve nothing, and report what needed an Engine

Then set the answer and run the same command again:

```bash
NOSTDB_SKILL_ENGINE_CHOICE=npx scripts/resolve-engine.sh nost_language_version 2
```

The answer is stored for **this session**, so later calls need nothing — do not ask twice, and do not
pass the variable again. A new session asks again, because somebody who chose not to install to get
through one afternoon should not still be living with it next week.

Neither route names a version, so both take the newest release. Exit `3` is the `none` answer.

A session is asked once. A new one asks again, because somebody who chose "no Engine" to get through
one afternoon should not still be living with it next week.

A non-interactive run is never prompted and never installs anything on its own. It exits `1` with
the exact commands, because a script that paused for a question nobody could answer would hang,
and one that installed software unasked is worse.

On exit `3`, run the action's AI-free reporting only and say what needed an Engine. Do not
approximate what the Engine would have returned.

**Windows.** NostDB publishes no Windows build, so resolution refuses there and says so rather than
offering an install that cannot work. The daemon implements only the Unix socket, and nothing in the
product compiles for Windows yet. WSL reports Linux and is a published target.

The order and the compatibility check are explained in [`RESOLUTION.md`](RESOLUTION.md).

## Step 2: run the action

`scripts/dispatch.sh <action> [arguments...]` prints the command an AI-free action invokes. Pass the
resolved command in `NOSTDB` and run exactly what it printed — it is runnable as it stands:

```bash
NOSTDB=$(scripts/resolve-engine.sh nost_language_version 2)
scripts/dispatch.sh build .        # prints the command
```

The resolved command is **substituted, not prefixed**. Prefixing does not compose: a project-local
resolution is `./node_modules/.bin/nostdb`, the no-install route is four words
(`npx --yes --package=nostdb nostdb`), and a mapping that chains two commands contains the command
twice, so there is nowhere to put a prefix.

It prints rather than runs so a user can be shown what will happen before it does.

Exit `0` mapped, `1` the action needs a model and has no AI-free mapping, `2` unknown action.

| Action | Serves | AI usage |
| --- | --- | --- |
| `build` | `/nostdb .` | optional |
| `build-nost` | `/nostdb . --nost` | optional |

| `sync` | `/nostdb .nostdb/root.nost --sync` | none |
| `query-cypher` | `/nostdb query --cypher '...'` | none |
| `view` | `/nostdb view .` | none |
| `plugin-add` | `/nostdb plugin add '...'` | none |
| `query-natural` | `/nostdb query "..."` | required |
| `enrich` | `/nostdb . --ai=full` | required |

### `/nostdb .` configures, analyzes, and writes

`build` is the whole of `/nostdb .`, not just the analysis step. It emits:

```bash
[ -f ./.nostdb/settings.json ] || nostdb init . ; nostdb build .
```

`init` creates `.nostdb/settings.json` and `.nostdb/root.nostdb`; `build` walks the tree, analyzes
what an analyzer covers, and commits what it found. `build-nost` adds `export --nost`, which writes
the canonical `.nostdb/root.nost`.

`init` is **guarded** rather than run unconditionally. It refuses an already-configured project and
exits `2` so that a re-run cannot discard configuration, and `/nostdb .` has to work the second time
as well as the first. The guard is the settings file `init` itself writes.

A bare `/nostdb` with no path means `.`.

An action is **not** required to be one CLI command, or to be named after one. `build` runs two
commands and `help` runs none — the Skill's surface is its own, and shaping it around what somebody
would ask for beats mirroring a command table.

What every AI-free action must do is **have the CLI do the work**. The Skill composes commands and
never computes an answer itself: two implementations of one question is two answers, and which one a
user gets would depend on the surface they happened to reach for.

A **`required` action with no model fails.** It does not fall back to a deterministic
approximation and report success: a caller who asked a question in English and got an answer
derived some other way has been told something untrue about where it came from.

What each declaration obliges is written out in [`ACTIONS.md`](ACTIONS.md).

## Natural language: the statement decides, not the label

Generate a proposal — the kind of request this is, and the openCypher for it — as JSON, and
hand it to the gate. The gate decides; the model does not.

```bash
printf '{"kind":"read","cypher":"MATCH (n) RETURN n LIMIT 10"}' | scripts/nl-gate.sh
```

| It prints | Do this |
| --- | --- |
| `execute` | show the statement, then run it |
| `confirm` | show the exact scope, and run nothing until somebody says so |
| `clarify` | ask the question, and run nothing |
| `refuse` | the proposal cannot be acted on at all |

Exit codes match that order: `0`, `1`, `2`, `3`, and `4` when the proposal could not be read.
Pass `confirmed` as the first argument only after a person has actually confirmed.

A write clause makes a statement a write however the proposal announced it, because the label
is the one part of a proposal that costs nothing to get wrong. **Ambiguity is not resolved by
confirmation** — confirming a request nobody has stated precisely is confirming this Skill's
guess at it, which is the failure that makes a natural-language surface untrustworthy rather
than merely wrong.

## Enrichment: the plan and the budget come first

1. build the structural database and **commit it**. Structural analysis of supported source
   spends no external tokens, and a usable generation must exist before enrichment starts, so
   an AI failure cannot erase structural facts;
2. produce a plan with `nostdb plan --format json`;
3. pipe that plan through the gate. Pass `non-interactive` when nobody can be asked:

```bash
nostdb plan --format json . | scripts/budget-check.sh
```

It prints `proceed`, `ask`, `skip`, or `refuse`, with exit codes `0`, `1`, `2`, `3`, and `4`
when the plan could not be read. `refuse` is not `skip`: a skip says nobody was asked, and a
refusal says somebody already answered.

4. only then send anything, and send an **analysis packet** from the Engine rather than a
   repository. Ask once, not per unit — asking per unit trains a user to approve without
   reading.

What a packet may contain, and what a partial result is, are in
[`ENRICHMENT.md`](ENRICHMENT.md).
