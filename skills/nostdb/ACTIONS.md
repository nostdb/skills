# The `/nostdb` action table

Every action declares what it needs from a model. That declaration is part of the action's
identity, not something discovered while it runs.

The reason is budgeting. A caller has to know before invoking an action whether it can cost
tokens, and an action that could quietly become AI-requiring is one nobody can plan for. It
is also how `--scan` means something: it selects over this column rather than hoping.

| Action | AI usage | What it does |
| --- | --- | --- |
| `/nostdb help` | none | describes the surface, answered by the Skill without an Engine |
| `/nostdb .` | optional | configures the project if it is not, analyzes it, and commits what it found; enrichment is the optional part |
| `/nostdb . --scan=ai` | required | the analyzers do not run; the same `.nostdb` is produced from a model's reading, and checked in staging before it replaces the project's |
| `/nostdb export .` | none | writes the graph as canonical `.nost`, once, from what is already built |
| `/nostdb convert .nostdb/root.nostdb root.nost` | none | converts between `.nost` and `.nostdb`, in whichever direction the extensions name; refuses an existing output unless `--replace` is passed |
| `/nostdb summary .` | none | reports the totals, the kinds present, and whether the container is sound |
| `/nostdb query --cypher '...'` | none | runs a statement the caller wrote |
| `/nostdb query '...'` | required | generates openCypher from a natural-language question |
| `/nostdb view .` | none | opens a viewer plugin |
| `/nostdb check root.nostdb` | none | hands a `.nostdb` or `.nost` to the Engine and reports what it breaks, records against the Schemas it holds included; the step that closes the `--scan=ai` loop |
| `/nostdb plugin add '...'` | none | installs a plugin through the CLI |
| `/nostdb preset` | none | lists the schema presets, and has the Engine validate one |
| `/nostdb preset project` | required | proposes what the repository is: name, stack, and what its directories are for |
| `/nostdb preset jpa` | required | proposes records in a preset's vocabulary, for the Engine to validate |

## What `none` obliges

An AI-free action **has the CLI do the work**. It does not compute an answer itself, and it does not
carry its own implementation of something the Engine already does.

That is the whole of the obligation. It is deliberately *not* a requirement that an action be one CLI
command, or be named after one: `/nostdb .` runs two, and `/nostdb help` runs none because the Skill is
the thing that knows what the Skill does. A surface shaped around what somebody would ask for is worth
more than one that mirrors a command table, and mirroring never bought anything the rule below does not
already buy.

What it protects against is a second engine. Two implementations of one question is two answers, and
the one a user gets would depend on which surface they happened to use — so every `none` row above is a
row a fixture can pin to the commands it runs.

### The action that runs five commands

`/nostdb summary` asks the Engine for every number it reports. Counting the graph in the Skill would
be a few lines of awk, and this is where that would look harmless: the report carries two pairs of
numbers that mean different things, a second implementation would quietly conflate them, and no test
of the command mapping would notice. Which pairs, and why they differ, is in `SKILL.md`, where
whoever renders the report reads.

The declared schema *names* have no read-only Engine command at all, so the count is what `summary`
reports. Reaching for the canonical `.nost` instead would mean `export`, which writes, and then
parsing the language. A Skill does neither.

### The one action that runs nothing

`/nostdb help` describes this Skill. It used to map to `nostdb help`, which meant reading a help message
required resolving an Engine first — and with none installed, resolution stops and asks whether to
install one. Nobody should have to install a database to find out what a Skill does.

### A preset is a vocabulary, which is why applying one is `required`

`/nostdb preset` lists what this Skill ships and hands a preset to `nostdb check`, because a preset is a
`.nost` document and the Engine is what reads one. That much is `none`: the Skill computes nothing and the
Engine validates.

`/nostdb preset jpa` is `required`, and the reason is the whole point of the boundary. A preset names what a
persistence mapping is called *once something has read it*; nothing in this Skill reads `@Entity`. Deriving
the facts from a preset AI-free would make the Skill a second analyzer — one reading annotations the
Engine's own analyzers do not read — and that is precisely what `none` forbids.

`/nostdb preset project` is `required` for the same reason and a plainer one: what a repository is *for* is
not in any file, so there is nothing for the CLI to read. It is the one preset no annotation selects — every
project has a name and a purpose — and `scripts/presets.py always` is how it is found rather than by guessing
a framework.

So the interpretation is the model's, the vocabulary is the preset's, and the validation is the Engine's. The
proposal's owner is `ai`, which is what makes a preset safe to modify: an `ai` contribution is withdrawable
on its own, so replacing a preset's facts does not touch what an analyzer wrote.

## What `optional` means, and does not

`optional` means the action completes without a model and does more with one. It does not
mean the action decides for itself: with no configured budget the contract requires asking once
rather than proceeding.

`--scan` has a second value, `default`, which is what a bare `/nostdb .` does and therefore has
no row of its own. The two are different pipelines rather than two settings of one: `default` is
`nostdb build`, where the analyzers read the source and AI is asked only about what they could not
resolve. `ai` does not build at all — a model reads every file and the Engine turns its
reading into the same `.nostdb`, which is checked in staging before it replaces the project's. [`SCAN.md`](SCAN.md) has the five steps.

That is why `ai` is `required` rather than `optional`. There is no second reader to fall back to:
without a model nothing reads the source, and building with the analyzers instead would report a
graph the caller did not ask for. The plan's `semantic_candidates` moves with the flag for the same
reason — under `ai` every scanned file is read, and the budget is checked against that.

Neither value spends nothing. `analysis.ai_mode` in `.nostdb/settings.json` takes `off`, which
is where a no-tokens guarantee lives, and the Engine reads it on every build.

Turning enrichment off does not turn materialization off either.
Not running `/nostdb export .` does not turn `.nost` off either — disabling it is an explicit
action, because an action not taken is not a request.

`/nostdb export .` is `none` rather than `optional` because an export involves no model at any
setting. It is also not a build: it writes what the database already holds, and the Engine
warns that the document will not be kept current, since writing it does not set
`database.nost` and no command sets it.

## What `required` accepts as failure

A `required` action with no model available fails. It does not fall back to a deterministic
approximation and report success, because a caller that asked a question in natural language and got
an answer derived some other way has been told something untrue about where the answer came
from.
