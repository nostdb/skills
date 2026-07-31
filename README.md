# skills

Independently installable Agent Skills for NostDB: the AI-capable extension of the `nostdb`
command surface.

## Install

```bash
npx skills add nostdb/skills
```

Install one skill by name:

```bash
npx skills add nostdb/skills --skill nostdb
```

By hand, copy `skills/nostdb` into `.agents/skills/nostdb` and reference its `SKILL.md` from
your project `AGENTS.md`.

## Layout

```text
skills/
├── nostdb/
│   ├── SKILL.md         # the definition an agent reads
│   ├── ACTIONS.md       # every action and what it declares about AI usage
│   ├── RESOLUTION.md    # which `nostdb` a Skill uses, and how it decides
│   ├── ENRICHMENT.md    # what is sent to a model, and what must be true first
│   ├── presets/         # vocabularies a proposal uses, and the Engine validates
│   └── scripts/         # the deterministic parts: resolution, dispatch, and the two gates
└── nostdb-analyzer-springboot/
    ├── SKILL.md         # the definition an agent reads
    ├── presets/         # the Spring Boot vocabulary, and what it covers
    └── scripts/         # listing the vocabulary, which needs no Engine
```

The second holds a vocabulary and no command surface. It names what a Spring Boot service states about
itself — the shapes on either side of a route, the constraints over them, the store that is there, the work
the framework invokes, and what the build declares — so a model reading one proposes the same names twice.
It runs the Engine through the first Skill rather than reaching into its folder, because a folder is what an
installer copies.

`skills/<name>/SKILL.md` is the path an installer discovers, and the skill folder is the unit
it copies. Everything a definition references therefore lives inside its own folder — a
reference reaching outside it would resolve in this repository and be missing from every
install. The repository verifier checks that, so the property holds rather than being
remembered.

`tests/` stays outside the skill folder on purpose. It verifies this repository and is run by
`scripts/verify-repository.sh` and by CI; shipping a test harness into every install would be
payload nobody asked for.

## What a Skill is here

An extension of the CLI, not a second database implementation, a competing command surface, or
a file writer. It resolves a compatible `nostdb` executable and calls it.

Every action declares what it needs from a model — see [`skills/nostdb/ACTIONS.md`](skills/nostdb/ACTIONS.md).
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

## Status

The deterministic surface around the model call is implemented: Engine resolution, the AI-free
dispatcher, the analysis-packet budget gate, and the natural-language gate, with a test suite
for each. Nothing here has ever called a model, and no test may — a model's output is not
reproducible even in principle, so what is testable is everything around the call.

See the root [`IMPLEMENTATION_PROGRESS.md`](https://github.com/nostdb/nostdb/blob/main/IMPLEMENTATION_PROGRESS.md)
for which increment built which part.

## Verify

```bash
./scripts/verify-repository.sh
```

## Licence

Apache-2.0. A Skill is meant to be read, forked, and replaced.
