
### Stage 35 verification

`skills`: `./scripts/verify-repository.sh` passed, with every suite green —
`resolution` 40 checks, `dispatch` 63, `presets` 10, `budget` its own, `natural language` 25, and the
Spring Boot preset suite. `nostdb-spec` and `nostdb-core`: their verifiers passed. Root:
`./scripts/verify-workspace.sh` passed.

**No assertion was relaxed.** Every suite runs its original checks against the Python, and the only thing that
changed in five of the six is the path invoked. Two mechanisms had to move, and both were mechanisms rather
than assertions:

- the pty driver ran the script as `["/bin/sh", script, …]`, which made it a second declaration of what the
  script was written in — wrong the moment the script changed language. It now execs the script and lets the
  shebang decide;
- the check that discovers which actions the dispatcher maps grepped `case` labels, which Python does not have.
  It reads the dispatcher's own `ACTIONS` now, and still decides what *maps* by running each — which is the
  part worth keeping, because `help` is an action that maps nothing.

`ACTIONS` is load-bearing rather than a list for a reader: an action absent from it is refused before any
branch runs, so a branch not named there is unreachable. A decorative list would have drifted.

### Two bugs the rewrite found, and one it did not

**Reading `/dev/tty` hung the suite.** The first draft of the key reader opened `/dev/tty`, which is the
obvious source for a keypress and is wrong here: a caller driving the menu through a pseudo-terminal writes to
the child's *standard input*, so the reader waited for ever on a key that had already arrived. The shell read
stdin, and so does this. It is also `os.read` rather than a buffered reader, which waits for more than the one
byte asked for.

**Detecting Windows needs both sources.** The suite reaches that branch with a fake `uname` on the path — the
only way to reach it from a machine that is not Windows. `platform.system()` uses the syscall and ignores a
fake binary, so three checks failed. Both are consulted now, `uname -s` first, and that is more correct than
either alone: under a POSIX layer the layer's own answer is what counts, because that is the environment the
npm and brew commands would run in, and where there is no `uname` at all — Windows-native Python — only
`platform.system()` can say so.

**`budget-check`'s two failing cases are shapes the contract permits, not shapes the CLI emits.** Against
today's output the shell reader worked, because `max_input_tokens` happens to be written first inside
`budget`. What it depended on was that order, and JSON member order carries no meaning — so moving one line in
the emitter would have made the gate read no limit and answer `ask` on a plan that should skip. Four cases pin
the reader to the document; two of them fail against the shell version.

### What this makes the Skill depend on

`python3`. The suite already needed it for the pty test and said so — "skipped where python3 is absent rather
than made a dependency of the suite" — and that is no longer a soft dependency. It is a real cost, recorded
rather than argued away: `/bin/sh` is present on more machines than `python3`.

What it buys is the two JSON readers, and the arithmetic. Shell has no floats, so a fractional token limit was
read as its integer prefix; now it is refused as the defect it is.

### Stage 35 closed

Every Acceptance Criterion passes.
