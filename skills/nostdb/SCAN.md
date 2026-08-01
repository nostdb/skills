# `--scan`: which reader produces the graph

Two readers, and they are not two settings of one pipeline. They are different pipelines that end in the
same place.

| | `--scan=default` | `--scan=ai` |
| --- | --- | --- |
| Who reads the source | the Engine's analyzers | a model |
| What produces the graph | `nostdb build` | a candidate `.nost` the model writes, converted into one |
| Cost of reading supported source | zero external tokens | every file is sent |
| What validates it | the analyzers cannot produce an invalid graph | `nostdb check` on the database, with a fix loop |
| AI usage | `optional` — enrichment on top, within budget | `required` — there is no other reader |

## `--scan=default`

`nostdb build` walks the tree, hands each file to the analyzer registered for its language, and commits what
they found. Enrichment is a second pass over what they could **not** cover, described in
[`ENRICHMENT.md`](ENRICHMENT.md).

This is the whole of a bare `/nostdb .`, and it is the one that spends nothing on supported source.

## `--scan=ai`

The analyzers do not run. **The deliverable is the `.nostdb`**, exactly as it is under `default` — what
changes is who read the source to produce it.

A model cannot write one. `.nostdb` is opaque and only the Engine writes it, so the model's output is a
candidate `.nost`, and `convert` is what turns it into the database. That intermediate is a mechanism, not a
second artifact: nothing downstream reads it, and it is the Engine that validates it on the way in.

```bash
nostdb init PATH                                                    # 1, when unconfigured
nostdb plan --format json --project PATH                            # 2, then the budget check
                                                                    # 3, the model writes CANDIDATE.nost
nostdb convert CANDIDATE.nost STAGING.nostdb                        # 4
nostdb check STAGING.nostdb                                         # 5
                                                                    # 6, the model fixes; back to 4
nostdb convert CANDIDATE.nost PATH/.nostdb/root.nostdb --replace    # 7
```

**Step 1 is not the analyzers.** `init` writes `.nostdb/settings.json` and an empty database, and creates the
directory step 7 writes into — without it, `convert` fails with no such file. It also means a valid
generation exists before the model has produced anything, so a model that produces nothing leaves a database
that opens.

**Step 2 is not optional, and it is where this pipeline is most expensive.** No AI call starts before a
visible plan and a budget check, and step 3 sends *every file* — so the plan is the only thing standing
between a caller and the cost of their whole repository. It runs through
[`scripts/budget-check.py`](scripts/budget-check.py) exactly as [`ENRICHMENT.md`](ENRICHMENT.md) requires.

> **The plan is only honest when `analysis.ai_mode` is `"full"`.** `nostdb plan` reads the mode from
> `.nostdb/settings.json` and has no flag for it, and `init` writes neither — so the default is `auto`,
> under which the plan counts only the files no analyzer covers. On a Java project that is a plan reporting
> almost nothing while the model is about to read everything, and a budget checked against it would pass a
> limit it should have stopped.
>
> So `--scan=ai` requires `"ai_mode": "full"` in the project's settings, and the caller sets it: a Skill
> that wrote settings would be changing state without the Engine. If it is not set, say what the plan
> under-reports rather than proceeding on it. A `--scan` option on `nostdb plan` would remove the whole
> problem and does not exist yet.

## What is validated is the database, and it is validated before it replaces anything

Step 5 is the whole of the validation: the `.nostdb` is read back and every record is checked against the
Schemas the container holds. The candidate document is never checked on its own — it is an intermediate the
Engine consumes, and the artifact anybody cares about is the database.

**Step 4 exists so step 5 can run before step 7.** `convert --replace` overwrites the project's database, and
a run that validated only afterwards would have destroyed the previous generation before learning anything
was wrong — which is the one thing the contract says a failed mutation must not do. So the model's output is
built into a **staging** database first, checked there, and only a candidate that survives is converted over
the real one.

The staging database is a validation artifact and nothing else. It is thrown away, and step 7 re-converts
from the same document rather than moving it into place: both writes are then the Engine's, and a Skill that
copied an opaque container around would be handling a format only the Engine is allowed to write.

Step 4 also catches what `check` cannot. A document that does not parse never becomes a database at all, so
`convert` failing *is* the diagnostic — there is nothing to check afterwards.

## The fix loop reads the diagnostics, not the exit code

This is the part that is easy to get wrong, and getting it wrong produces a database full of violations that
every command calls valid.

Schema validation is soft by contract, so a database whose every record violates its Schema still exits `0`
and prints `valid, generation 2, 1 nodes`. `convert` commits such a document too, warning as it goes.

```text
warning: NOST_SCHEMA_VIOLATION: node n_019fbc2d-... (Thing): the required field count of type integer is missing
staging.nostdb: valid, generation 2, 1 nodes, 0 edges, 0 links, 1 schemas
```

So the loop is driven by **whether step 5 printed a diagnostic at all**, not by what it exited with. Each one
names the record by identifier and labels and says what it breaks, which is what a model needs to correct the
document rather than regenerate it. A container has no line to point at, which is the price of validating the
database rather than the document.

Two diagnostics are **not** failures and must not be fixed away:

- `NOST_UNRESOLVED_ENDPOINT` — a name that resolves to nothing becomes a Placeholder, which is the
  contract's answer to a missing symbol rather than a defect. A model that deleted the edge to silence it
  would be removing a fact the source contains;
- anything the source genuinely says. A warning is a reason to look, not a reason to make the document say
  something else.

**Three attempts, then stop.** A loop that kept going would spend a budget on a model that has already
demonstrated it cannot satisfy the Engine, and each attempt costs what the whole file costs. On the third
failure, report the remaining diagnostics and the candidate's path, and **do not run step 7** — a database
nobody could validate is not one to put over a database that currently opens.

## `--replace` overwrites the database, and that is the risk to state

Step 7 needs `--replace`, because step 1 already created `root.nostdb`. The flag does exactly what it says:
the database becomes what the candidate holds, and whatever was there is gone.

On a project this scan is the first reader of, there is nothing to lose. On a project that has been built,
**there is**: the analyzers' facts, any AI contribution from a previous run, and anything a person
contributed. `--scan=ai` is not an increment on top of them. Say so before running step 7 on a project that
already has a database, and let the caller decide — a caller who wanted a second opinion from a model and
got their analyzer facts deleted was not warned by a flag they never typed.

A proposal that *adds* to an existing graph is a change set applied with `nostdb apply`, which carries an
owner and can be withdrawn. That is a different action and is not this one.

## What is never done

- **the Skill never writes `.nostdb`, and never writes settings either.** Every command above is the
  Engine's; the Skill composes them. The candidate is a `.nost` document, which the root contract permits a
  Skill to write;
- **the analyzers are never run and then discarded.** `--scan=ai` does not build first and throw it away: it
  does not build. Running both and keeping one would spend the analyzers' time to produce nothing, and
  report a token bill for work a caller could have had free;
- **a candidate is never written to `.nostdb/root.nost`.** That path is what `export` materializes and what
  `sync` reconciles against, so putting an unvalidated document there would make the Engine's own
  materialization the thing a model overwrote.
