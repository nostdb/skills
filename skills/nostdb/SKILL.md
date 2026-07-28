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

## Step 1: resolve the Engine

Do this before every action that touches a database, and pass the contract version the action
needs rather than an Engine version:

```bash
scripts/resolve-engine.sh nost_language_version 2
scripts/resolve-engine.sh query_subset_version 1 1.4.0   # third argument permits a pinned npx
```

It prints the command to use and nothing else. Exit `0` resolved, `1` nothing compatible
found, `2` used incorrectly.

It installs nothing. If no compatible Engine is found, report the exact commands that would
install one and stop — a Skill that installed software because it needed some is one nobody
can safely run in a directory they do not own.

The order and the compatibility check are explained in [`RESOLUTION.md`](RESOLUTION.md).

## Step 2: run the action

`scripts/dispatch.sh <action> [arguments...]` prints the `nostdb` command an AI-free action
invokes. Run exactly what it printed, prefixed by the resolved command. It prints rather than
runs so a user can be shown what will happen before it does.

Exit `0` mapped, `1` the action needs a model and has no AI-free mapping, `2` unknown action.

| Action | Serves | AI usage |
| --- | --- | --- |
| `help` | `/nostdb help` | none |
| `build` | `/nostdb . --ai=off` | none |
| `build-nost` | `/nostdb . --nost` | optional |
| `sync` | `/nostdb .nostdb/root.nost --sync` | none |
| `query-cypher` | `/nostdb query --cypher '...'` | none |
| `view` | `/nostdb view .` | none |
| `plugin-add` | `/nostdb plugin add '...'` | none |
| `query-natural` | `/nostdb query "..."` | required |
| `enrich` | `/nostdb . --ai=full` | required |

An **AI-free action must call the same Core command the command surface calls**, not an
equivalent one. Two implementations of one action is two answers to one question, and which
one a user gets would depend on the surface they happened to reach for.

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
