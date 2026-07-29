# The `/nostdb` action table

Every action declares what it needs from a model. That declaration is part of the action's
identity, not something discovered while it runs.

The reason is budgeting. A caller has to know before invoking an action whether it can cost
tokens, and an action that could quietly become AI-requiring is one nobody can plan for. It
is also how `--ai=off` means something: it is a filter over this column, not a hope.

| Action | AI usage | What it does |
| --- | --- | --- |
| `/nostdb help` | none | describes the surface, answered by the Skill without an Engine |
| `/nostdb .` | optional | configures the project if it is not, analyzes it, and commits what it found; enrichment is the optional part |
| `/nostdb . --ai=off` | none | the same build, with enrichment refused rather than skipped |
| `/nostdb . --ai=full` | required | enrichment is not optional, and the action fails without it |
| `/nostdb . --nost` | optional | the same, materializing the canonical `.nost` as well |
| `/nostdb .nostdb/root.nost --sync` | none | reconciles the two representations |
| `/nostdb query --cypher '...'` | none | runs a statement the caller wrote |
| `/nostdb query "..."` | required | generates openCypher from a question |
| `/nostdb view .` | none | opens a viewer plugin |
| `/nostdb plugin add '...'` | none | installs a plugin through the CLI |

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

### The one action that runs nothing

`/nostdb help` describes this Skill. It used to map to `nostdb help`, which meant reading a help message
required resolving an Engine first — and with none installed, resolution stops and asks whether to
install one. Nobody should have to install a database to find out what a Skill does.

## What `optional` means, and does not

`optional` means the action completes without a model and does more with one. It does not
mean the action decides for itself: `--ai=off` refuses enrichment, and with no configured
budget the contract requires asking once rather than proceeding.

`--ai=off` on an already-enabled project turns off *enrichment*, not materialization.
Omitting `--nost` does not turn `.nost` off either — disabling it is an explicit action,
because a flag's absence is not a request.

## What `required` accepts as failure

A `required` action with no model available fails. It does not fall back to a deterministic
approximation and report success, because a caller that asked a question in English and got
an answer derived some other way has been told something untrue about where the answer came
from.
