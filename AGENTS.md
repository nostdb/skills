# skills Agent Instructions

## Inheritance

This repository is a child of the NostDB root superproject. The root `AGENTS.md`
at <https://github.com/nostdb/nostdb> is the governing contract.

This file only narrows the root rules for the Skill boundary. It must not weaken any root
product, safety, or ownership boundary. If this file and the root contract appear to
conflict, the root contract wins, the current valid behavior stays unchanged, and the exact
conflict is recorded in the root `IMPLEMENTATION_PROGRESS.md`.

## Language policy

Write everything in this repository in English only, regardless of the language a request is
written in. This covers documentation, skill definitions, prompts, identifiers, comments,
commit messages, diagnostics, and every line a Skill prints.

## Repository layout

A Skill lives at `skills/<name>/SKILL.md`, which is the path an installer discovers, and the
skill folder is the unit it copies.

- the definition's frontmatter declares `name`, matching its directory, and `description`,
  which is what an agent selects the skill by;
- everything a definition references lives inside its own folder. A reference reaching outside
  it resolves in this repository and is missing from every install;
- a script a definition invokes is committed executable;
- `tests/` and `scripts/verify-repository.sh` stay outside the skill folders. They verify this
  repository rather than travelling with an install.

`scripts/verify-repository.sh` enforces all of it. Do not add a `SKILL.md` anywhere else: a
definition an installer cannot find is a Skill nobody can ask for.

## Ownership boundary

A Skill is the AI-capable extension of the CLI and implements no database behavior.

Permitted:

- skill definitions, their action tables, and their declared AI usage;
- prompts, and the analysis packets sent with them;
- resolving a compatible `nostdb` executable and invoking it;
- rendering what the Engine returned.

Prohibited:

- any `.nostdb` writer. Only the Engine writes one;
- a parser, storage engine, synchronizer, analyzer, or query engine;
- a second copy of the grammar, the conformance fixtures, or the root PRD;
- a plugin manager, which exists once in `nostdb-cli`;
- an action that changes state without the Engine.

## Presets

A preset is a `.nost` document under `skills/<name>/presets/`, and an index beside it saying which
annotations each one covers.

Two things it is:

- a **vocabulary** — the names a proposal uses once something else has read the source. `nostdb-spec` accepts
  a consequence rather than solving it: a record may name a schema that was never declared, so a misspelled
  label is indistinguishable from an intentional bare one and no syntax can tell them apart while schemas
  remain optional. Fixing the names on the producing side is the only place they can be;
- a **validation target** — the Engine checks it, because it is a `.nost` file and the Engine reads those.

**A preset is not an analyzer, and deriving a fact from one AI-free is prohibited.** Nothing in this
repository reads `@Entity`. A Skill that interpreted a preset's annotations itself would be a second
analyzer — one reading what the Engine's own analyzers do not read — which the AI-free rule below exists to
prevent. So an action that applies a preset is `required`: the interpretation is the model's, the vocabulary
is the preset's, and the validation is the Engine's.

Two rules a preset must follow, both tested:

- it declares no label a build already writes. A schema is unowned, so a preset sharing a name with a builtin
  label is replaced on the next build — the preset would vanish and the only sign would be a warning;
- it declares no label called `Schema`. NostDB already has schemas, and a preset is made of them.

A preset's records reach the graph through `nostdb apply`, owned by `ai`. That ownership is what makes a
preset safe to modify: an `ai` contribution is withdrawable on its own, so replacing a preset's facts never
touches what an analyzer wrote.

## Analyzer Skills

A vocabulary for one framework is its own Skill, named `nostdb-analyzer-<framework>`. A framework a project
does not use is a document nobody should have to install, which is why these are separate rather than folded
into `nostdb`.

`nostdb` finds them at run time and never references one. An installer copies a skill *folder*, so a path to
a sibling resolves here and is absent everywhere else — `scripts/analyzers.py` therefore looks at the
directory it is installed in and reports whichever siblings are there. Correct beside one, beside several,
and beside none.

Only `SKILL.md`'s `name` and `description` are read. Reaching further into a sibling — its presets, its
schemas — would couple one Skill to another's internal layout; a definition is the part a Skill publishes.

Two rules, both tested:

- **an analyzer Skill is optional.** Nothing fails when none is installed. What is not acceptable is reading
  a framework by hand while a Skill for it is installed: that produces the same facts under different names,
  and the graph then holds two vocabularies for one subject with no way to tell which a query should use;
- **using one is announced, and announcing one that is not installed is refused.** A Skill claiming a
  vocabulary it does not have would be claiming a reading nobody performed, and the output would look exactly
  like the one that did.

## Invariants this repository must never break

- **An AI-free action has the CLI do the work.** It never computes an answer itself. Two
  implementations of one question is two answers, and which one a user gets would depend on the
  surface they reached for.
- **An action need not be one CLI command, or be named after one.** `/nostdb .` runs two and
  `/nostdb help` runs none. The Skill's surface is its own, shaped around what somebody would ask
  for rather than around a command table — what is fixed is who does the work, not how the
  request is spelled.
- **Every action declares its AI usage**, and that declaration is part of its identity.
- **No AI call starts before a visible plan and a budget check.**
- **A natural-language write shows its exact scope and requires confirmation.**
- **An ambiguous request asks and executes nothing.**
- **No unpinned `latest` fallback** for a state-changing non-interactive action.
- **A `required` action with no model fails** rather than falling back to an approximation
  and reporting success.
- Secrets never reach a prompt, a packet, a log record, a diagnostic, or output.

## Testing expectations

The testable surface is everything around the model call, because a model's output is not
reproducible even in principle and no fixture can pin it.

- every AI-free action, with a fixture pinning the CLI commands it invokes — one, several, or
  none, and named however the Skill names it;
- Engine resolution: the order, and the version check that decides compatibility;
- packet construction: what is included, and that a secret never is;
- the budget check: what it permits and what it refuses;
- refusals: a write without confirmation, an ambiguous request, a `required` action with no
  model.

No test may call a model.

## Safety and external actions

- Never execute analyzed source code.
- Never place a credential in a prompt, a packet, a fixture, a diagnostic, or output.
- Do not create remote repositories, add remotes, push to a new remote, publish packages,
  create releases, or modify registries without explicit user authorization.
- Do not use destructive Git commands or broad deletion.

## Stage workflow

Implementation sequencing is tracked in the root `IMPLEMENTATION_PROGRESS.md`, not here.
