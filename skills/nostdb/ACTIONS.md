# The `/nostdb` action table

Every action declares what it needs from a model. That declaration is part of the action's
identity, not something discovered while it runs.

The reason is budgeting. A caller has to know before invoking an action whether it can cost
tokens, and an action that could quietly become AI-requiring is one nobody can plan for. It
is also how `--ai=off` means something: it is a filter over this column, not a hope.

| Action | AI usage | What it does |
| --- | --- | --- |
| `/nostdb help` | none | describes the surface |
| `/nostdb .` | optional | builds or refreshes the database; enrichment is the optional part |
| `/nostdb . --ai=off` | none | the same build, with enrichment refused rather than skipped |
| `/nostdb . --ai=full` | required | enrichment is not optional, and the action fails without it |
| `/nostdb . --nost` | optional | the same build, materializing the canonical `.nost` |
| `/nostdb .nostdb/root.nost --sync` | none | reconciles the two representations |
| `/nostdb query --cypher '...'` | none | runs a statement the caller wrote |
| `/nostdb query "..."` | required | generates openCypher from a question |
| `/nostdb view .` | none | opens a viewer plugin |
| `/nostdb plugin add '...'` | none | installs a plugin through the CLI |

## What `none` obliges

An AI-free action **must call the same Core command the command surface calls**. Not an
equivalent one, and not its own implementation of the same idea.

The Skill is an extension of the CLI, not a second engine. Two implementations of one action
is two answers to one question, and the one a user gets would depend on which surface they
happened to use. Every `none` row above is therefore a row that a fixture can pin, and the
root contract requires exactly that.

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
