#!/usr/bin/env python3
"""Resolves the nostdb command a Skill should use, and prints it.

The order is fixed by the product contract: project-local, then a compatible global. Both are cheap: a file
test, then one `--version --json` on the first candidate that exists.

# Why npx is no longer a silent third step

It used to be. Passing a pinned version made `npx --yes --package=nostdb@<version> nostdb` the automatic answer
whenever nothing was installed, so every action paid npx's fetch and start-up cost and nobody had chosen to.
Resolution looked slow; what was slow was the command resolution handed back.

npx is still available and still pinned. It is now one of three things a caller can *choose* when nothing is
installed, and the choice is remembered so the question is asked once.

# The decision, and where it is remembered

With nothing installed and no remembered choice:

  - an interactive session is asked once — install it, or do not install and run it with npx — and the answer
    holds for the rest of that session;
  - a non-interactive one exits 1 with the exact commands, unchanged. A script that paused for a prompt nobody
    could answer would hang, and one that installed software unasked is worse.

The choice is remembered for the **session** that made it, not for ever, and it records a decision a person
made rather than a resolved path: a cached path would be a lie the moment the Engine was installed, upgraded,
or removed, and re-probing costs one process.

The question is asked with a list the arrow keys move through, falling back to a typed answer on a terminal
that will not enter raw mode.

# The version report is parsed rather than pattern-matched

The compatibility check read the reply with
`tr -d ' \\n' | sed -n 's/.*"<key>":\\[\\([^]]*\\)\\].*/\\1/p'` — a JSON array taken with a character class that
stops at the first `]`, from a document with every space removed. It worked against what the Engine writes,
and what it depended on was that: a leading `.*` is greedy, so the *last* match won, and a member written
after the one wanted would have been read instead. JSON member order carries no meaning, so an emitter
reordering one line would have changed which contract this reports as supported.

Exit codes: 0 resolved, 1 nothing compatible and no decision, 2 used incorrectly,
            3 the caller chose to continue with no Engine, 130 the prompt was interrupted.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RESOLVED, UNRESOLVED, USAGE, NO_ENGINE, INTERRUPTED = 0, 1, 2, 3, 130

# The candidates a project may hold, in the order the contract fixes.
LOCAL_CANDIDATES = ("./node_modules/.bin/nostdb", "./bin/nostdb")


def note(message: str = "") -> None:
    """Standard error, always.

    Standard output carries the resolved command and nothing else, so a caller can use it directly — a message
    printed there would become the command.
    """
    print(message, file=sys.stderr)


def usage() -> None:
    note("usage: resolve-engine.py <required-contract> <required-version> [pinned-version]")
    raise SystemExit(USAGE)


def session_key() -> str:
    """The POSIX session, which is what "session" means and is shared by every process in one terminal.

    Where there is no controlling terminal the session id is the process group leader's and is not useful, so
    the parent shell stands in: repeated calls from one shell agree, and a new shell asks again.
    """
    try:
        sid = os.getsid(0)
    except (AttributeError, OSError):
        sid = 0
    if sid:
        return str(sid)
    return f"shell{os.getppid()}"


def supports(reply: str, contract: str, required: str) -> bool:
    """Whether a `--version --json` reply says this contract version is supported.

    The argument is the *contract key*, which is what the version registry publishes and what every document
    names: `nost_language_version`. The report answers with what a build supports, which is a list, so its key
    is that plus an `s`. Asking for the singular key found nothing in a real report, and every fake in this
    repository's suite agreed with the question rather than with the Engine.

    A match is on a whole value, so supporting 12 is not read as supporting 1. The required version arrives as
    text because it came from a command line; a reply lists numbers, so both are compared as text after the
    numbers are rendered — which keeps `2` and `2.0` distinct rather than quietly equal.
    """
    try:
        document = json.loads(reply)
    except (json.JSONDecodeError, ValueError):
        return False
    if not isinstance(document, dict):
        return False
    supported = document.get(f"{contract}s")
    if not isinstance(supported, list):
        return False
    return any(
        not isinstance(held, bool) and isinstance(held, int) and str(held) == required
        for held in supported
    )


def compatible(candidate: str, contract: str, required: str) -> bool:
    """Whether a candidate answers `--version --json` and supports the contract version asked for.

    A command that does not answer is not an old nostdb; it is not nostdb, because something on the path with
    the right name and the wrong behavior is worse than nothing.
    """
    try:
        finished = subprocess.run(
            [candidate, "--version", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    if finished.returncode != 0:
        return False
    return supports(finished.stdout, contract, required)


def resolve_installed(contract: str, required: str) -> str | None:
    """The installed Engine to use, or `None`.

    1. Project-local. A project that pinned a version did so on purpose, and a global installation overriding
       it would mean one checkout giving two people different answers.
    2. A compatible global.

    One pass, stopping at the first that answers, so an installed Engine costs a single process rather than one
    per candidate.
    """
    for candidate in LOCAL_CANDIDATES:
        if os.access(candidate, os.X_OK) and compatible(candidate, contract, required):
            return candidate
    found = shutil.which("nostdb")
    if found and compatible(found, contract, required):
        return found
    return None


def refuse_windows() -> None:
    """Where nothing can be offered, because nothing in the product builds there.

    NostDB publishes four targets, all macOS and Linux. Windows is recorded as intended and not buildable:
    `nostdb-server` implements only the Unix domain socket while the protocol contract specifies a named pipe
    for Windows, so nothing in the product compiles there yet.

    A shell that reports MINGW, MSYS, or CYGWIN is a POSIX layer on Windows. WSL reports Linux and is a
    supported platform, so it is not caught.

    `uname -s` first, then `platform.system()`. Both, because they answer different questions and either can be
    the one that matters: under a POSIX layer the layer's own answer is what counts, since that is the
    environment the npm, brew, and npx commands would run in — and where there is no `uname` at all, which is
    Windows-native Python, only `platform.system()` can say so.
    """
    reported = ""
    try:
        finished = subprocess.run(["uname", "-s"], capture_output=True, text=True, check=False)
        if finished.returncode == 0:
            reported = finished.stdout.strip()
    except OSError:
        pass
    system = reported or platform.system() or "unknown"
    if not system.startswith(("MINGW", "MSYS", "CYGWIN")) and system != "Windows":
        return
    note("NostDB publishes no Windows build, so there is nothing to install or run here")
    note("the daemon implements only the Unix socket, and nothing in the product compiles for Windows yet")
    note("run this under WSL, which reports Linux and is a published target")
    raise SystemExit(UNRESOLVED)


def remember(state: Path, decision: str) -> None:
    """Written whole and moved into place, so a reader sees one decision or the other.

    A partial line would be a decision nobody made. Every failure here is ignored: not remembering an answer
    costs one more question, and failing the resolution over it costs the action.
    """
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        partial = state.with_name(state.name + ".partial")
        partial.write_text(decision + "\n", encoding="utf-8")
        partial.replace(state)
    except OSError:
        try:
            state.with_name(state.name + ".partial").unlink(missing_ok=True)
        except OSError:
            pass


def normalize(answer: str) -> str:
    """One spelling table for every source of the decision.

    A prompt, the environment, and the stored file all pass through here, so
    `NOSTDB_SKILL_ENGINE_CHOICE=i` and a stored `install` cannot mean different things.
    """
    return {
        "i": "install", "install": "install",
        "x": "npx", "npx": "npx",
        "n": "none", "no": "none", "none": "none",
    }.get(answer.strip().lower(), "")


def target_for(pinned: str) -> str:
    return f"nostdb@{pinned}" if pinned else "nostdb"


def npx_command(pinned: str) -> str:
    return f"npx --yes --package={target_for(pinned)} nostdb"


def install_commands(pinned: str) -> None:
    note(f"  npm install --global {target_for(pinned)}")
    note("  brew install nostdb/tap/nostdb")
    note(f"  {npx_command(pinned)}   # no permanent install")


def options_for(pinned: str) -> list[tuple[str, str]]:
    """The list a person moves through, as key and label."""
    return [
        ("install", f"Install {target_for(pinned)} globally with npm"),
        ("npx", "Do not install; run it with npx each time" + (f" (pinned to {pinned})" if pinned else "")),
    ]


def draw(options: list[tuple[str, str]], selected: int, first: bool) -> None:
    """The list, redrawn in place on standard error.

    `first` is what tells a redraw to go back to the top of the list rather than adding another copy below it.
    The hint sits one row under the options, so it is cleared and rewritten with them.
    """
    if not first:
        sys.stderr.write(f"\r\033[{len(options)}A")
    for at, (_, label) in enumerate(options):
        if at == selected:
            sys.stderr.write(f"  \033[1m[x] {label}\033[0m\n")
        else:
            sys.stderr.write(f"  [ ] {label}\n")
    sys.stderr.write("\033[K\033[2m  up/down or j/k to move, enter to choose\033[0m")
    sys.stderr.flush()


def read_key() -> str:
    """One keypress from standard input, named.

    An arrow key arrives as three bytes — escape, `[`, a letter — so escape reads two more. `j` and `k` move
    too: somebody who lives in a pager expects them to, and it costs two lines.

    `os.read` on the descriptor rather than a buffered reader, and standard input rather than `/dev/tty`. Both
    matter: a buffered reader waits for more than one byte, and a caller driving this through a pseudo-terminal
    writes to the child's standard input — reading `/dev/tty` instead would block for ever on a key that had
    already arrived.
    """
    first = os.read(0, 1)
    if not first:
        return "quit"
    if first == b"\x1b":
        rest = os.read(0, 2)
        return {b"[A": "up", b"[B": "down"}.get(rest, "other")
    return {
        b"\n": "enter", b"\r": "enter", b" ": "enter",
        b"k": "up", b"j": "down",
        b"\x03": "quit", b"q": "quit",
    }.get(first, "other")


def choose_with_keys(options: list[tuple[str, str]]) -> str | None:
    """The arrow-key list, or `None` where a terminal will not enter raw mode or the question was abandoned.

    The terminal is restored however this ends, including an interrupt. One left in raw mode is a broken shell,
    which is a worse outcome than any answer to this question.
    """
    try:
        import termios
        import tty
    except ImportError:
        return None
    try:
        saved = termios.tcgetattr(0)
    except (termios.error, OSError):
        return None

    selected = 0
    try:
        tty.setraw(0)
        draw(options, selected, first=True)
        while True:
            key = read_key()
            if key == "enter":
                break
            if key == "quit":
                selected = -1
                break
            if key == "up":
                selected = max(0, selected - 1)
            elif key == "down":
                selected = min(len(options) - 1, selected + 1)
            draw(options, selected, first=False)
    except KeyboardInterrupt:
        termios.tcsetattr(0, termios.TCSADRAIN, saved)
        note()
        raise SystemExit(INTERRUPTED) from None
    finally:
        try:
            termios.tcsetattr(0, termios.TCSADRAIN, saved)
        except (termios.error, OSError):
            pass
    note()
    return None if selected < 0 else options[selected][0]


def choose_typed(pinned: str) -> str:
    """A typed answer, where the list could not be drawn.

    A terminal that will not enter raw mode must not stop the question being asked — the point is the decision,
    and the arrow keys are how it is comfortable rather than how it is possible.
    """
    sys.stderr.write(f"choice for this session [i/{'x/' if pinned else ''}n]: ")
    sys.stderr.flush()
    try:
        return normalize(input())
    except (EOFError, KeyboardInterrupt):
        return ""


def do_install(pinned: str, contract: str, required: str) -> None:
    """Install, then re-probe.

    Unpinned unless the caller passed a version, and that does not breach the product contract. What the
    contract forbids is an unpinned *fallback*: "no unpinned `latest` fallback for a state-changing
    non-interactive action". A fallback is what happens when nobody chose, and with no choice this resolves
    nothing and exits 1. Installing happens because somebody picked it from a list, which is the opposite.

    The repeatedly-executed path keeps its pin. npx runs on every action, which is where "the command that ran
    last week and the command that runs tonight are different programs" actually bites.
    """
    if not shutil.which("npm"):
        note("npm is not on the path, so this cannot install nostdb")
        install_commands(pinned)
        raise SystemExit(UNRESOLVED)
    target = target_for(pinned)
    # Echoed before it runs. Installing software is a visible act even when it was agreed to once.
    note(f"installing {target} globally, as chosen for this session")
    note(f"  npm install --global {target}")
    finished = subprocess.run(
        ["npm", "install", "--global", target], stdout=sys.stderr, stderr=sys.stderr, check=False
    )
    if finished.returncode != 0:
        note("the install failed; nothing was resolved")
        raise SystemExit(UNRESOLVED)
    # Re-probed rather than assumed. An install that reported success and left nothing usable is exactly the
    # case a caller must not be told is fine.
    found = resolve_installed(contract, required)
    if found:
        print(found)
        raise SystemExit(RESOLVED)
    # With no pin that is the newest release genuinely not supporting what was asked for, which is worth
    # saying plainly rather than as a version.
    note(f"{target} installed and still does not support {contract} {required}")
    raise SystemExit(UNRESOLVED)


def refuse_without_a_decision(contract: str, required: str, pinned: str) -> None:
    """What a caller with no terminal gets, which is the normal case: an agent runs this.

    A marker line rather than prose, because the caller acting on it is a program deciding what to ask a
    person. The tokens are the ones `NOSTDB_SKILL_ENGINE_CHOICE` takes, so what is read here can be passed
    straight back.
    """
    note(f"no nostdb supporting {contract} {required} was found")
    note("decision required: install | npx | none")
    note(f"  install  npm install --global {target_for(pinned)}")
    note(f"  npx      {npx_command(pinned)}   # installs nothing")
    note("  none     resolve nothing, and report what needed an Engine")
    note()
    note("set NOSTDB_SKILL_ENGINE_CHOICE to install, npx, or none and run this again.")
    note("the answer is stored for this session, so ask once and later calls need nothing.")
    raise SystemExit(UNRESOLVED)


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        usage()
    contract, required = argv[0], argv[1]
    pinned = argv[2] if len(argv) > 2 else ""

    # Overridable so a test never touches real state, and so a CI run can state the decision up front instead
    # of being asked.
    stated_state = os.environ.get("NOSTDB_SKILL_STATE")
    state = Path(
        stated_state
        if stated_state
        else Path(os.environ.get("TMPDIR") or tempfile.gettempdir())
        / f"nostdb-skill-engine.{session_key()}"
    )

    # An installed Engine is used without consulting the decision at all, so a remembered "none" cannot
    # strand a caller that has one.
    found = resolve_installed(contract, required)
    if found:
        print(found)
        raise SystemExit(RESOLVED)

    refuse_windows()

    # A remembered choice, or one the environment states, is honored without asking again.
    choice = normalize(os.environ.get("NOSTDB_SKILL_ENGINE_CHOICE", ""))
    if choice:
        # Stored as well as honored. The prompt below is unreachable without a terminal, which is exactly how
        # a Skill is normally run — an agent invokes it — so the environment is the *usual* way a decision
        # arrives, not an escape hatch. Remembering it is what makes one question cover a session instead of
        # the caller passing the answer on every call.
        remember(state, choice)
    else:
        try:
            choice = normalize(state.read_text(encoding="utf-8").splitlines()[0])
        except (OSError, IndexError, UnicodeDecodeError):
            choice = ""

    # Asked only when a person can answer. A script blocked on a prompt is worse than one that refuses.
    if not choice and sys.stdin.isatty() and sys.stderr.isatty():
        note(f"no installed nostdb supports {contract} {required}.")
        note()
        picked = choose_with_keys(options_for(pinned))
        choice = normalize(picked) if picked else choose_typed(pinned)
        # An unreadable answer is not remembered. Storing a guess would make the rest of the session act on
        # something nobody chose, and this way the question is simply asked again.
        if choice:
            remember(state, choice)

    if choice == "npx":
        # Unpinned unless the caller passed a version, which is the no-install route asked for.
        #
        # This is the weaker half of the trade and worth being plain about: npx runs on *every* action, so with
        # no pin the command that ran last week and the command that runs tonight can be different programs,
        # and the output is the only evidence. What keeps it honest is that it is never a default — with no
        # choice this resolves nothing — and the compatibility check asks whatever arrives what contract
        # versions it supports before an action uses it.
        print(npx_command(pinned))
        raise SystemExit(RESOLVED)
    if choice == "install":
        do_install(pinned, contract, required)
    if choice == "none":
        note("continuing with no Engine, as chosen for this session")
        note("actions that need one will report what they could not do")
        raise SystemExit(NO_ENGINE)

    refuse_without_a_decision(contract, required, pinned)


if __name__ == "__main__":
    main(sys.argv[1:])
