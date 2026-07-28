# skills

Independently installable Agent Skills for NostDB: the AI-capable extension of the `nostdb`
command surface.

**Status: scaffolding.** The action table is written; no action is implemented. See the root
[`IMPLEMENTATION_PROGRESS.md`](https://github.com/nostdb/nostdb/blob/main/IMPLEMENTATION_PROGRESS.md)
for which increment builds which part.

## What a Skill is here

An extension of the CLI, not a second database implementation, a competing command surface,
or a file writer. It resolves a compatible `nostdb` executable and calls it.

Every action declares what it needs from a model — see [`nostdb/ACTIONS.md`](nostdb/ACTIONS.md).
That declaration is part of the action's identity rather than something discovered while it
runs, because a caller has to know before invoking an action whether it can cost tokens.

## What a Skill never does

It never writes `.nostdb`. Only the Engine does. A Skill may draft a `.nost` or propose a
versioned change set, and the Engine validates ownership, generation, endpoints, schemas,
constraints, and evidence before anything is committed.

A natural-language **read** shows the generated Cypher and runs it. A natural-language
**write** shows its exact scope and waits for confirmation. An **ambiguous** request asks a
question and executes nothing — guessing which of two readings was meant is the failure mode
that makes a natural-language surface untrustworthy.

## Licence

Apache-2.0. A Skill is meant to be read, forked, and replaced.
