---
name: nostdb
description: Build, query, and synchronize a NostDB property graph of a codebase through the nostdb command surface. Use when asked to create or refresh a .nostdb, materialize the canonical .nost, run an openCypher query over a code graph, ask in natural language how parts of a codebase connect, convert between .nost and .nostdb, open a graph viewer, or install a NostDB plugin.
license: Apache-2.0
metadata:
  version: 0.1.4
  engine: latest
  requires:
    nost_language_version: 3
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
/nostdb . --scan=ai                the same, but AI is required; fails without a model
/nostdb export .                   write the graph as canonical .nost
/nostdb convert <in> <out>         convert between .nost and .nostdb, either way
/nostdb summary .                  report how much is in the database, and of what kinds
/nostdb query --cypher '...'       run a statement you wrote
/nostdb query "..."                ask in English; the generated Cypher is shown
/nostdb view .                     render the graph through a viewer plugin
/nostdb preset                     list the schema presets this Skill ships
/nostdb preset jpa                 propose records for a preset, and apply them
/nostdb plugin add '...'           install a plugin from a pinned GitHub source
/nostdb help                       this

Options:
  --scan=default|ai                default: analyzers first, AI for what they could not
                                   resolve. ai: the same, with the AI half required
  --cypher '<statement>'           run a statement you wrote instead of a question
  --replace                        let convert overwrite an existing output; takes no value
```

`/nostdb .` with no path means the current folder. It configures the project if it is not configured,
analyzes the whole tree, and writes `.nostdb/settings.json` and `.nostdb/root.nostdb`.

It does **not** write `.nost` unless the project already has it enabled. Materialization is an explicit
choice rather than a side effect of building, and `/nostdb export .` is how it is asked for.

### `--scan` names which reader does the work

Two values. Both run both passes, and what differs is whether the second one is allowed to be missing:

| Written | What happens | AI usage |
| --- | --- | --- |
| `--scan=default` | the deterministic analyzers read what they cover, and AI is asked about what they could not resolve, within the configured budget | `optional` |
| `--scan=ai` | the same two passes, with the AI half **required** — the action fails rather than reporting a structural-only result | `required` |

**`ai` does not mean AI alone.** Nothing suppresses the deterministic analyzers: no CLI option does, and the
contract requires structural analysis of supported source to spend zero external tokens and a valid structural
generation to be committed before any enrichment. So the analyzers always read first, and this value decides
whether a run without a model is a result or a failure.

`default` is what a bare `/nostdb .` does, so it gets no *invocation* line of its own — there would be
nothing to say about it that the line above does not already say. It appears in the surface's `Options` block
because a value a reader cannot see is not documented, and saying it explicitly is how somebody asks for the
default on purpose.

To spend **nothing**, set `analysis.ai_mode` to `off` in `.nostdb/settings.json`. That is a project's standing
answer rather than a flag somebody has to remember, and the Engine reads it on every build.

### `convert` writes one representation from the other

In whichever direction the extensions name: `.nost` to `.nostdb` validates then commits, `.nostdb` to
`.nost` writes the canonical document. Two identical extensions are refused, because that is a copy.

**It refuses an output that already exists**, and `--replace` is what permits overwriting one. Pass the
flag only when somebody asked for it. Supplying it on their behalf would turn a refusal they were meant to
see into a file they did not know they lost.

Converting onto a configured project's `.nostdb/root.nostdb` replaces whatever the database held, with no
check of what changed since. `nostdb sync` is the command that compares a project's two representations
against a recorded baseline and refuses when both moved — it is not on this surface, so an agent asked to
reconcile a project rather than convert a file should say so and name that command rather than reach for
`--replace`.

### `/nostdb export .` writes the document, once

It writes `.nost` from what is already in the database. It does **not** build first, so run `/nostdb .`
before it if the source has changed — and it does not need to be run at all on a project that already has
`.nost` enabled, where every build keeps it current.

`nost` is the default and the only representation this Engine writes, so there is no option to select one.
The reserved spelling for the day there is a second is recorded in the root `IMPLEMENTATION_PROGRESS.md`,
not here: a help screen that names a flag doing nothing describes a Skill that does not exist.

**The Engine warns that the document will not be kept current**, because writing it does not set
`database.nost`, and no command sets it. Say so when relaying the warning rather than treating it as a
failure: the file is written and correct, and it is a snapshot rather than something maintained.

## Step 1: resolve the Engine

Do this before every action that touches a database, and pass the contract version the action
needs rather than an Engine version:

```bash
scripts/resolve-engine.sh nost_language_version 2
scripts/resolve-engine.sh query_subset_version 1
```

Pass no version. **This Skill always resolves the newest release**, which is what `engine: latest` in its
frontmatter declares. It names the **contract** it needs and lets the install be whatever newest release
satisfies it; a version baked into a Skill definition is a version that goes stale in a document nobody
re-reads.

`metadata.version` is this Skill's own version and moves with the product's release number. It is not a
version of anything it resolves — the two are different questions, and a reader seeing one number would
otherwise reasonably assume the Skill was tied to that Engine.

A third argument is still accepted, and a caller who has a reason to pin one gets the pinned `npx` option
as well. That is for somebody who asked; it is never what happens by default. What the product contract
forbids is an unpinned `latest` **fallback** — the thing that happens when nobody chose — and with no
choice this resolves nothing and exits `1`.

It prints the command to use and nothing else. Exit `0` resolved, `1` nothing compatible found
and no decision, `2` used incorrectly, `3` the caller chose to continue with no Engine.

An installed Engine resolves in one process, and a pinned version no longer makes `npx` the
automatic answer. It used to: passing one meant every action paid npx's fetch and start-up cost
without anyone choosing it.

### With nothing installed, ask once for the session

Exit `1` prints `decision required: install | npx | none`. **You** ask the question, because you are
the one who can be answered — this script has no terminal when an agent runs it, so its own prompt
never appears.

**Ask it the way your own surface asks anything else, and show the options as a list.** A list is what
somebody reads; a sentence with three words buried in it is not.

**Use a native single-select if you have one** — a question with options a person actually picks. That
is where a real `[x]` comes from: your harness draws the control and hands back the answer, so the box
somebody ticks is a box that does something. Prefer this whenever it exists.

With no native picker, print the list and say what to reply with:

```text
1) install   npm install --global nostdb         stays installed
2) npx       npx --yes --package=nostdb nostdb   installs nothing, fetches each run
3) none      resolve nothing, and report what needed an Engine
```

Reply with the word or the number.

What not to do is **imitate** a control — writing empty brackets into a message where nothing can tick
them. A list of boxes that cannot be ticked looks like it works and then does not, which is worse than
either a real picker or a plain list. Numbers a reader can type are a list; brackets a reader cannot
click are a broken widget.

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
| `export` | `/nostdb export .` | none |
| `convert` | `/nostdb convert <in> <out>` | none |
| `summary` | `/nostdb summary .` | none |
| `query-cypher` | `/nostdb query --cypher '...'` | none |
| `view` | `/nostdb view .` | none |
| `plugin-add` | `/nostdb plugin add '...'` | none |
| `preset-check` | `/nostdb preset` | none |
| `query-natural` | `/nostdb query "..."` | required |
| `enrich` | `/nostdb . --scan=ai` | required |
| `preset-apply` | `/nostdb preset jpa` | required |

### `/nostdb .` configures, analyzes, and writes

`build` is the whole of `/nostdb .`, not just the analysis step. It emits:

```bash
[ -f ./.nostdb/settings.json ] || nostdb init . ; nostdb build .
```

`init` creates `.nostdb/settings.json` and `.nostdb/root.nostdb`; `build` walks the tree, analyzes
what an analyzer covers, and commits what it found. It writes no `.nost` — `export` is a separate action,
because the Engine separates them and because a build that materialized as a side effect would be doing
something nobody asked for.

`export` emits one command and takes no guard:

```bash
nostdb export --nost .
```

The surface says `export` and the command says `--nost`, which is deliberate rather than a mismatch. `nost`
is the surface's default, where a person reads it; the flag is spelled at the boundary, where it runs. The
CLI requires it so that a later representation cannot silently change what a bare `export` means, and
spelling it keeps that guarantee whatever the surface later grows.

`init` is **guarded** rather than run unconditionally. It refuses an already-configured project and
exits `2` so that a re-run cannot discard configuration, and `/nostdb .` has to work the second time
as well as the first. The guard is the settings file `init` itself writes.

A bare `/nostdb` with no path means `.`.

### `/nostdb summary .` reports what a database holds

`summary` is five reads, and it writes nothing. It emits:

```bash
nostdb query 'CALL nostdb.build_status()' --project .
nostdb query 'MATCH (n) RETURN nostdb.link_alias(n) AS alias, count(n) AS total ORDER BY total DESC' --project .
nostdb query 'MATCH (n) RETURN labels(n) AS labels, count(n) AS total ORDER BY total DESC, labels' --project .
nostdb query 'MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS total ORDER BY total DESC, type' --project .
nostdb check ./.nostdb/root.nostdb
```

Present them in that order as one report: the generation and the totals, where those records came
from, node labels with their counts, edge types with theirs, then whether the container is sound.
Either spelling of the path names one database — `/nostdb summary .nostdb/` and `/nostdb summary .`
agree, because a query resolves the nearest configured project at or above what it is given. A bare
`/nostdb summary` means `.`.

Two pairs of numbers in that report are **different questions**, and reporting either as the other
describes a database nobody has:

- **the totals are the root's; the breakdowns cover the links too.** `build_status` answers from the
  root alone and a read sees the union, so one link is enough to report 5 nodes and then break down
  11. The per-source count is what reconciles them: a blank alias is the root, each other row is a
  link's contribution;
- **schemas declared are not kinds present.** A build declares a schema for every label its
  analyzers can write, so a project holding three kinds of node still declares fourteen. `check`
  reports the declared count; the breakdowns count what actually carries each kind.

The declared schema **names** have no read-only Engine command at all. Report the count, and say
that is what the Engine offers — the names exist only in the canonical `.nost`, which `export`
writes and only a parser would read, and a Skill does neither.

`check` runs last because it is the one call that can fail on a report that is otherwise fine: it
exits `3` when the container holds an error diagnostic. Last means the counts have already printed,
so the failure reads as the answer to "is this database sound" instead of hiding the summary.

An action is **not** required to be one CLI command, or to be named after one. `build` runs two,
`summary` runs five, and `help` runs none — the Skill's surface is its own, and shaping it around what
somebody would ask for beats mirroring a command table.

What every AI-free action must do is **have the CLI do the work**. The Skill composes commands and
never computes an answer itself: two implementations of one question is two answers, and which one a
user gets would depend on the surface they happened to reach for.

A **`required` action with no model fails.** It does not fall back to a deterministic
approximation and report success: a caller who asked a question in English and got an answer
derived some other way has been told something untrue about where it came from.

What each declaration obliges is written out in [`ACTIONS.md`](ACTIONS.md).

### Presets: a vocabulary the Engine validates

A preset is the names a proposal uses **once something else has read the source**, written as a `.nost`
document in [`presets/`](presets/jpa.nost). `scripts/presets.sh` lists them, says which one covers an
annotation, and needs no Engine — a preset is part of this Skill, and asking somebody to install a database
to find out which presets exist is the wrong order of operations.

Two things a preset is:

- a **vocabulary**. `nostdb-spec` accepts a consequence rather than solving it — a record may name a schema
  that was never declared, so a misspelled label is indistinguishable from an intentional bare one, and "no
  syntax can tell the two apart while schemas remain optional". Fixing the names on the *producing* side is
  the only place they can be told apart. Without a preset, a model proposing `Entity` today and `JpaEntity`
  tomorrow produces two unvalidated labels and no error;
- a **validation target**. `preset-check` hands the document to `nostdb check`, because a preset is a `.nost`
  file and the Engine is what reads one. This Skill holds no validator, so a malformed preset fails before
  it is ever offered to a model.

**What a preset is not is an analyzer.** Nothing here reads `@Entity`. Deriving a fact from a preset without
a model would make this Skill a second analyzer — reading annotations the Engine's own analyzers do not read
— which is what the rule about an AI-free action having the CLI do the work exists to prevent. So
`preset-apply` is `required`: the interpretation is the model's, and the validation is the Engine's.

#### How a preset is chosen

By the Engine's own report, not by naming a framework. A build reports the annotations it saw and did **not**
interpret, and `scripts/presets.sh for Entity` answers which preset covers one. Naming the framework instead
would need a list of frameworks this build knows of and cannot read, which is a closed allowlist by another
route.

#### The order, which is the enrichment order

1. build and **commit** the structural graph first, so an AI failure cannot erase structural facts;
2. read the uninterpreted annotations from the build, and find the preset that covers them;
3. `preset-check` it, so a broken preset fails before a token is spent;
4. plan and check the budget, exactly as [`ENRICHMENT.md`](ENRICHMENT.md) requires;
5. the model proposes a change set whose owner is `ai` and whose evidence is `inferred`, using the preset's
   names and nothing else;
6. show the exact scope, take a confirmation, and `nostdb apply` it. The Engine validates the generation,
   the endpoints, the ownership, and the evidence, and a failed apply preserves the last valid generation.

Step 5's owner matters. An `ai` contribution is withdrawable on its own, so a preset's facts can be replaced
without touching what an analyzer wrote — which is what keeps a preset safe to modify.

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
nostdb plan --format json --project . | scripts/budget-check.sh
```

`--project`, for the same reason `build` uses it. Release 0.1.0 refuses a positional path to `plan`, and
a later build refused it too when an option came first — so the spelling documented here was one that
worked in neither. `--project` is accepted by every version in either position.

It prints `proceed`, `ask`, `skip`, or `refuse`, with exit codes `0`, `1`, `2`, `3`, and `4`
when the plan could not be read. `refuse` is not `skip`: a skip says nobody was asked, and a
refusal says somebody already answered.

4. only then send anything, and send an **analysis packet** from the Engine rather than a
   repository. Ask once, not per unit — asking per unit trains a user to approve without
   reading.

What a packet may contain, and what a partial result is, are in
[`ENRICHMENT.md`](ENRICHMENT.md).
