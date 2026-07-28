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

## Invariants this repository must never break

- **An AI-free action calls the same Core command the CLI calls.** Not an equivalent one.
  Two implementations of one action is two answers to one question.
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

- every AI-free action, with a fixture proving it invokes the same Core command as the CLI;
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
