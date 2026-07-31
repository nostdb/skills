---
name: nostdb-analyzer-springboot
description: Read a Spring Boot service into a NostDB graph — its routes' request and response shapes, the constraints stated over them, the data store it connects to, the work the framework invokes on a schedule or a message, and what its build declares. Use when asked what endpoints a Spring Boot project exposes and what they accept or return, which tables or collections it touches, what validates or authorizes a request, what runs on a schedule, which datasource or settings a profile configures, or what a Gradle or Maven build depends on.
license: MIT
metadata:
  version: 0.1.6
  engine: latest
  requires:
    nost_language_version: 3
    change_set_version: 1
    query_subset_version: 1
---

# NostDB Spring Boot vocabulary

A **vocabulary** for facts a Spring Boot service states about itself, and nothing else. It reads no
source, holds no parser, and writes no database. What it ships is [a `.nost` document](presets/springboot.nost)
naming twelve kinds of record and fourteen relations, so that a model reading a service proposes the same
names today and next month.

The `nostdb` Skill is what runs the Engine. This one supplies the names, and the two meet in whoever is
using them: nothing here reaches into that Skill's folder, because an installer copies a skill folder and a
reference outside it is absent once installed.

## What it is not

**It is not an analyzer.** Nothing here reads `@Scheduled` or `application.yaml`. Deriving a fact from this
preset without a model would make this a second analyzer — reading what the Engine's own analyzers do not
read — and an AI-free action is required to have the Engine do the work rather than compute an answer
beside it.

**It writes nothing.** A proposal reaches the graph through `nostdb apply`, which validates the base
generation, the ownership, the endpoints, the schemas, and the evidence before committing. The owner is
`ai:<contract-digest>`, which is what makes a proposal safe to redo: an `ai` contribution is withdrawable on
its own, so replacing one never touches what an analyzer wrote.

## The actions

| Action | AI usage | What it does |
| --- | --- | --- |
| list the vocabulary | none | `scripts/presets.py list` — answered from this folder, no Engine |
| have it validated | none | `nostdb check` reads the preset like any other `.nost` document |
| find what a build did not read | none | the Engine's own build report and two queries below |
| propose records | required | a model reads the source and writes a change set in these names |

Proposing is `required` and fails without a model rather than falling back. A caller who asked what a
service exposes and got an answer derived some other way has been told something untrue about where it came
from.

## Java and Kotlin, both

The vocabulary names framework facts, not language ones, so it does not change between the two. What differs
is where a project writes them, and one difference is worth knowing:

Kotlin states a request type's constraints on a `data class`'s primary-constructor properties —
`data class NewUser(@NotBlank val email: String)` — and Java states them on fields. Both are reported as
uninterpreted annotations by a build, which is what step 1 relies on. Until `graph_schema_version` 10 the
Kotlin ones were read and dropped, so a build reported none of them; a project built by an older Engine will
report them after a rebuild.

`build.gradle.kts` and `settings.gradle.kts` are Kotlin, so an analyzer reads them as source and they never
appear as unread files. Their `dependencies {}` and `include()` calls are still unread — those are calls to a
language analyzer — so find them by path, as step 2 says.

## Step 1: let the Engine say what it could not read

Build first. `/nostdb .` through the `nostdb` Skill, or `nostdb build --project .` directly. The report ends
with the two things this Skill needs, and both are free — a structural build spends no external tokens:

```
endpoints  2 from spring
note: no framework analyzer here interprets Component, NotBlank, ResponseStatus, Scheduled; enrichment is what reads them
```

The route records already exist. The annotation names are what to look up:

```bash
scripts/presets.py for Scheduled      # -> springboot
scripts/presets.py for Component      # -> exits 1: nothing here covers it
```

`Component` exiting 1 is correct rather than a gap to fill. This preset declares no `Bean`, so dependency
injection has no names here to offer, and claiming `@Service` or `@Autowired` would point a model at
records that do not exist.

## Step 2: find the documents no analyzer read

A build reports uninterpreted *annotations*. It does not report an uninterpreted config file, because a
settings document is a `File` the scan recorded like any other. Two queries find them, and the Engine runs
both:

```bash
nostdb query "MATCH (f:File) WHERE f.precision = 'unsupported' RETURN f.path AS path ORDER BY path" --project .
nostdb query "MATCH (f:File) WHERE f.language IN ['yaml','toml','properties','sql'] RETURN f.path AS path, f.language AS language" --project .
```

The first is the broader question — every file present that nothing read — and catches a format neither
query anticipated. The second names the four this vocabulary has words for.

A Gradle build script does **not** appear in either: `build.gradle.kts` is Kotlin, and an analyzer read it.
Its declarations are still unread — a `dependencies {}` block is a call to a language analyzer — so find
those by path rather than by precision.

## Step 3: propose, in these names

Read the source, then write a change set. Two rules about its shape, both of which the Engine enforces
rather than trusts:

- **every record carries evidence**, with the path, the content digest, `method: ai_inferred`, and a
  confidence score. An `ai` owner without evidence is refused;
- **the base generation is the one you read.** A change set computed against a graph that has moved is
  refused rather than rebased, because it resolved names against something the producer never saw.

### An edge into a record a build wrote needs its identifier

Five relations reach `Endpoint`, `File`, `Method`, or `Directory`: `ACCEPTS`, `RETURNS`, `RUNS`,
`DECLARES_SETTING`, and `ROOTED_AT`. A change set names an endpoint by opaque identifier, so ask for the
record itself and read it out:

```bash
nostdb query "MATCH (e:Endpoint) RETURN e AS record, e.method AS method, e.path AS path" \
  --project . --format json
```

```json
{"columns": ["record", "method", "path"],
 "rows": [[{"node": "n_019fb6a0-43b7-7942-8c96-a7c7fcf8341c"}, "POST", "/users"]]}
```

`{"node": "n_…"}` is the value an endpoint takes: `"source": {"local": "n_019fb6a0-…"}`. Match the record by
the properties you can see — a route by its method and path, a file by its path — and use the identifier
beside them.

Two things this does not survive. A record reached through a `@link` belongs to another database and a write
may not touch it, so check `nostdb.source(e)` when a project has links. And an identifier read from one
generation names the same record in the next unless a build removed it, which is what the base generation
check is for: propose against the generation you read.

`nostdb export --nost .` writes the same identifiers as each record's reserved `id` property. Prefer the
query for one pattern and the export when reading a whole graph.

### Do not propose a list-valued property

Five fields are lists: `Request.path_variables`, `query_parameters`, and `headers`, `Table.primary_key`, and
`Collection.indexes`. **Leave them out too.** A change set's property reader takes a boolean, a string, and a
number; an array is refused with `unsupported property value`, even though the `.nost` language has list
properties and the preset declares these as `string[]`.

Name the singular facts you can: a column is a `TableColumn` record whether or not the key it belongs to is
recorded, and a path variable is visible in the route's own path. Do not flatten a list into a comma-joined
string — that puts a format in the graph every later reader has to parse, and the field is declared a list so
that it holds one when the route exists.

### Two things that must not reach the graph

**A datasource has no URL field, and that is not an omission to work around.** `jdbc:postgres://user:pw@host/db`
carries a credential, and the root contract forbids one reaching a graph file. Record `kind`, `driver`,
`host`, `port`, `database`, and `schema_name` — the parts that matter, none of which can hold a secret — and
never reconstruct the URL into another field.

**A setting that holds a secret is recorded without its value.** Set `secret: true` and omit `value`. A
password, a token, an API key, a connection string with a user in it: the key is worth knowing and the value
is not this graph's to hold. `secret: false` or absent means the value is there because it was safe, not
that nobody looked.

## What it does not cover

**Persistence mappings.** `@Entity`, `@Column`, and the repository interfaces over them belong to the `jpa`
preset the `nostdb` Skill ships. Two presets declaring one label would leave whichever applied last
standing.

The division is by source. `jpa` describes what a class says it maps to; this describes the store that is
there, from DDL, migrations, and configuration. They meet on a string: `Entity.table` and `Table.name` hold
the same name, and a query joins them on it.

**Dependency injection**, for the reason step 1 gives.

**Anything a deterministic analyzer already reads.** The route itself is one: `@GetMapping` produces an
`Endpoint` for free, and proposing a second record for it would put two answers in the graph to one
question.
