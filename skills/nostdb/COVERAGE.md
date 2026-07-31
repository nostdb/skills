# What a build did not read, and who reads it

A build says what it could not interpret. This is what to do with that, when more than one thing can read
it and their answers have to end up in one graph.

The worked example throughout is a project using both Spring Boot and Flyway: one has a Skill, the other
does not.

## The shape

```text
1. /nostdb .                     the Engine builds and reports what it did not read
2. read the report               annotation names, and the files nothing analyzed
3. for each, is there a Skill?   installed -> use it. not installed -> say so. none exists -> read it here
4. propose                       each producer writes a change set in its own vocabulary
5. reconcile                     where two producers describe one thing, they upsert one record
6. ask                           where they disagree on a value, the user decides
7. one graph                     one record, several contributions, every evidence kept
```

Steps 1 and 2 are free and reproducible: a structural build spends no external tokens and says the same thing
twice. Everything from 3 on costs a model, which is why the report comes first — it is what makes the cost
bounded rather than "read the repository".

## Step 1 and 2: the report is the input

```
endpoints  2 from spring
note: no framework analyzer here interprets Component, NotBlank, ResponseStatus, Scheduled; enrichment is what reads them
recorded   8 files, 4 with no analyzer for their language
```

Three things are in there. The **frameworks** a deterministic analyzer recognised, so those routes already
exist and nothing should propose them again. The **annotation names** nothing interpreted. And a count of
files nothing read, which the queries in the Spring Boot Skill's step 2 turn into paths.

A build does not name a framework it cannot read — naming one would need a list of frameworks it knows of and
cannot interpret, which the root PRD's section 4 forbids. So Flyway does not appear as "Flyway". It appears as
`db/migration/V1__users.sql`, a `.sql` file with `precision = unsupported`.

That is why step 3 works from two lists rather than one: annotation names, and unread paths.

## Step 3: who reads each thing

For an annotation, ask the preset index:

```bash
scripts/presets.sh for NotBlank      # this Skill's presets
```

For a Skill outside this one, the agent is what knows which are installed — a Skill cannot read another
Skill's folder, because an installer copies a folder and a reference outside it is absent once installed. So
the question is asked where the answer is: whatever is running these Skills sees both.

Three cases, and they are different:

| Case | What to do |
| --- | --- |
| a Skill covers it and is installed | use it, and use its vocabulary |
| a Skill covers it and is not installed | say which, and how to install it. Do not read the source instead |
| nothing covers it | read the source here, and propose with no preset |

The middle one matters. Reading Spring Boot by hand when `nostdb-analyzer-springboot` exists produces the
same facts under different names, and the graph then holds two vocabularies for one subject with no way to
tell which a query should use. Naming the Skill is more useful than an answer that has to be redone.

The third is Flyway in this example. There is no Flyway Skill, so a model reads the migrations directly. It
still needs names — and the names to use are the ones an installed preset already declares for that subject.
A migration creates a table, and `Table` and `TableColumn` are what the Spring Boot preset calls one. Reusing
them is what makes step 5 possible at all.

## Step 4: each producer proposes separately

One change set per producer, not one combined. Two reasons, and both are in the model rather than a
preference:

- **a change set carries one owner.** An `ai:<contract-digest>` names the contract that produced it, and two
  producers running different prompts against different sources are two contracts;
- **an owner is what can be withdrawn.** Redoing the Flyway reading should replace the Flyway facts and leave
  the Spring Boot ones alone, which is exactly what `RemoveContribution` does per owner. One combined set
  makes that impossible.

Each also states its own evidence — the path it read, the digest of those bytes, `method: ai_inferred`, and a
confidence. That confidence is the axis step 6 uses.

## Step 5: two producers, one record

Where two producers describe the same thing, the second **upserts the record the first created** rather than
creating another. Ask the graph for the identifier:

```bash
nostdb query "MATCH (t:Table) RETURN t AS record, t.name AS name" --project . --format json
```

```json
{"rows": [[{"node": "n_0198a1b2-c3d4-7e5f-8a9b-0c1d2e3f4b04"}, "users"]]}
```

Then propose `upsert_node` with that `id`. The Engine merges: one record, both contributions, both evidences.
Verified:

```nost
node n_0198a1b2c3d47e5f8a9b0c1d2e3f4b04: Table {
  name: "users",
  schema_name: "public"

  @by "ai:sha256:abcdef…" unit "u_…a99" {
    @evidence { producer: "springboot-preset", … }
  }

  @by "ai:sha256:ffffff…" unit "u_…aff" {
    @evidence { producer: "flyway-reader", path: "db/migration/V1__users.sql", … }
  }
}
```

`name` came from one and `schema_name` from the other, and each producer's evidence names itself. That is the
"one schema" the two readings end up in: not a merge that picks a winner, but one record that records who
said what.

**Match on a property, never on a position.** A table is matched by its name, a route by its method and path.
Two records that happen to be returned in the same order are not the same record, and the order of a result
is undefined without `ORDER BY`.

**Do not do this across a link.** A record reached through `@link` belongs to another database and a write may
not touch it. Check `nostdb.source(t)` when a project has links.

## Step 6: where they disagree

Two producers can say different things about one property. Spring Boot's configuration says a datasource is
`demo`; a migration says the table is in schema `public`; a JPA mapping says a column is `TEXT` and the DDL
says `VARCHAR(320)`.

A property holds one value, so the later proposal wins it. **Both evidences remain**, which is what makes the
disagreement findable rather than lost:

```bash
nostdb query "MATCH (t:Table) RETURN t.name AS name, nostdb.evidence(t) AS evidence" --project . --format json
```

So the rule is: propose the reading you are confident in, and **when two producers disagree on a value that
matters, say so and let the user decide.** Do not average them, do not prefer the newer one, and do not
prefer your own. What to show:

- the property, and the two values;
- which producer said each, from the evidence;
- the confidence each declared, and the path and range each read.

A confidence is comparable because the Engine keeps it. It did not until `change_set_version`'s evidence
table was written down — every proposal was stored as `extracted`, the value reserved for a fact read
directly out of source, so an inference and an extraction looked identical. A build that predates that will
show every contribution as `extracted`, and a rebuild is what fixes it.

Silence is the failure mode to avoid here. A graph where one producer quietly overwrote another reads as
agreement.

## What this does not do

It does not install a Skill. Naming one and the command to install it is where this stops, for the reason
Engine resolution stops there: something that installed software because it needed some is not safe to run in
a directory somebody does not own.

It does not decide which producer is right. That is step 6, and it is the user's.

It does not run without a model past step 2. Steps 1 and 2 are the Engine's and cost nothing; every step
after reads source, and a `required` action with no model fails rather than approximating.
