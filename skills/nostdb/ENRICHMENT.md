# Enrichment: what is sent, and what has to be true first

## A packet, not a repository

A Skill never sends a repository. It asks the Engine for an **analysis packet**: one source
unit's records, the relations among them, the names that resolved to nothing, a bounded set
of excerpts, and a summary of the units an edge reaches.

The bound is a property of the packet's shape rather than a rule the Skill follows. A packet
does not grow when the repository does, so "compact" is something the Engine guarantees and
the Skill cannot accidentally undo.

## The order, and why it is this order

1. **build the structural database, and commit it.** Structural analysis of supported source
   spends no external tokens, and the contract requires a usable generation to exist before
   any enrichment starts. AI failure then cannot erase structural facts, because they were
   already durable when it began;
2. **produce a plan.** `nostdb plan` reports what would be enriched and what it could cost;
3. **check the plan against the budget.** The check compares the *top* of the estimate: a
   call that could exceed a hard limit never starts;
4. **only then, send anything.**

A Skill that sent a packet and then reported the cost would be reporting a decision it had
already made.

## What the check decides

| Situation | What happens |
| --- | --- |
| a hard token limit is configured and the estimate fits | enrichment proceeds |
| a hard limit is configured and the estimate could exceed it | enrichment does not start |
| no hard limit is configured | the estimate is shown and the user is asked, once |
| no hard limit, and the session is non-interactive | enrichment is skipped |
| `ai_mode` is `off` | enrichment is refused, not skipped quietly |

"Asked once" is the whole of it. A Skill that asked per unit would train a user to approve
without reading, which is worse than not asking.

Skipping in a non-interactive session is not a failure. A build that stopped because nobody
was there to answer would make every unattended run depend on a person being present, and
the structural database — the part that matters most — is already committed by then.

## What a partial result is

A run that enriched some units and not others reports `semantic: partial`. It does not
report success.

Partial, truncated, unvalidated, or out-of-scope output is never recorded as an
authoritative cache hit, so a later run reaches the same units again rather than believing
they were done. A completed batch is checkpointed, so that later run does not pay twice for
the work that did succeed.

## What comes back, and what may not

AI may attach evidence or a semantic contribution to an existing record. It may not re-emit
a deterministic import, call, inheritance, or package edge as an independent fact.

The packet shows those edges deliberately. A model that can see what is already established
can add to it; one that cannot would have to guess, and its guesses would arrive looking
exactly like the facts an analyzer proved.
