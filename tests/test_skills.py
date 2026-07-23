import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "portable"
sys.path.insert(0, str(ROOT / "scripts"))
import install_adapter as adapter_module  # noqa: E402
from install_adapter import install as adapter_install  # noqa: E402
from nostdb_core import native_command, npx_command  # noqa: E402
from nostdb_source import (  # noqa: E402
    SourceError,
    digest as source_digest,
    install as source_install,
)


SKILLS = (
    "nostdb",
    "nostdb-visualize",
)


def invoke(*arguments, cwd=None, env=None):
    return subprocess.run(
        [str(argument) for argument in arguments],
        cwd=str(cwd) if cwd else None,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def tree_hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.temporary = Path(tempfile.mkdtemp(prefix="nostdb-skills-test-"))

    def tearDown(self):
        shutil.rmtree(self.temporary)

    def test_repository_verifier_and_portable_frontmatter(self):
        result = invoke(sys.executable, ROOT / "scripts" / "verify_skills.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skills: 2", result.stdout)
        for name in SKILLS:
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            header = text.split("---", 2)[1].strip().splitlines()
            self.assertEqual({line.split(":", 1)[0] for line in header}, {"name", "description"})
            self.assertIn("name: " + name, header)

    def test_layout_and_core_pin_are_persisted_without_losing_configuration(self):
        for layout, source in (
            ("centralized", ".nostdb/graph.nostdb"),
            ("colocated", "graph.nostdb"),
            ("single", "project.nostdb"),
        ):
            project = self.temporary / layout
            result = invoke(
                sys.executable,
                ROOT / "scripts" / "nostdb_project.py",
                "init",
                "--project",
                project,
                "--layout",
                layout,
                "--core-version",
                "0.0.1",
                "--module-id",
                "11111111-1111-1111-1111-111111111111",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["source"], source)
            self.assertTrue((project / source).is_file())
            config = (project / "nostdb.toml").read_text(encoding="utf-8")
            self.assertIn('layout = "{}"'.format(layout), config)
            self.assertIn('core_version = "0.0.1"', config)
            self.assertIn('core_provider = "auto"', config)
            self.assertIn('database = "graph.ndb"', config)
            self.assertIn('"{}" = "11111111-1111-1111-1111-111111111111"'.format(source), config)

        project = self.temporary / "single"
        config_path = project / "nostdb.toml"
        config_path.write_text(config_path.read_text(encoding="utf-8") + "# retained\n", encoding="utf-8")
        result = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "configure",
            "--project",
            project,
            "--layout",
            "colocated",
            "--core-version",
            "0.1.1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        config = config_path.read_text(encoding="utf-8")
        self.assertIn("# retained", config)
        self.assertIn('layout = "colocated"', config)
        self.assertIn('core_version = "0.1.1"', config)
        self.assertIn('"project.nostdb" = "11111111-1111-1111-1111-111111111111"', config)

        occupied = self.temporary / "occupied"
        occupied.mkdir()
        (occupied / "unrelated.txt").write_text("preserve\n", encoding="utf-8")
        refused = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "init",
            "--project",
            occupied,
            "--layout",
            "single",
        )
        self.assertEqual(refused.returncode, 3)
        self.assertIn("nonempty directory", refused.stderr)
        self.assertFalse((occupied / "nostdb.toml").exists())
        allowed = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "init",
            "--project",
            occupied,
            "--layout",
            "single",
            "--allow-nonempty",
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertEqual((occupied / "unrelated.txt").read_text(encoding="utf-8"), "preserve\n")

    def test_core_version_mismatch_is_explicit(self):
        project = self.temporary / "version"
        fake = self.temporary / "nostdb-fake"
        fake.write_text("#!/usr/bin/env python3\nprint('nostdb 9.9.9')\n", encoding="utf-8")
        fake.chmod(0o755)
        initialized = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "init",
            "--project",
            project,
            "--layout",
            "single",
            "--core-version",
            "0.0.1",
            "--core-binary",
            fake,
            "--module-id",
            "11111111-1111-1111-1111-111111111111",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        mismatch = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_core.py",
            "resolve",
            "--project",
            project,
            "--binary",
            fake,
        )
        self.assertEqual(mismatch.returncode, 3)
        self.assertIn("Core version mismatch: expected 0.0.1", mismatch.stderr)
        self.assertIn("found 9.9.9", mismatch.stderr)

        configured = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "configure",
            "--project",
            project,
            "--core-version",
            "9.9.9",
        )
        self.assertEqual(configured.returncode, 0, configured.stderr)
        matched = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_core.py",
            "resolve",
            "--project",
            project,
            "--binary",
            fake,
        )
        self.assertEqual(matched.returncode, 0, matched.stderr)
        self.assertEqual(Path(matched.stdout.strip()), fake.resolve())
        details = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_core.py",
            "resolve",
            "--project",
            project,
            "--binary",
            fake,
            "--json",
        )
        self.assertEqual(json.loads(details.stdout)["database"], "graph.ndb")
        self.assertEqual(json.loads(details.stdout)["provider"], "native")

    def test_native_provider_trust_boundary_and_installed_only_policy(self):
        project = self.temporary / "providers"
        binaries = {}
        for name in ("explicit", "environment", "path"):
            binary = self.temporary / ("nostdb-" + name)
            binary.write_text(
                "#!{}\nimport sys\nprint('nostdb 0.0.1')\n".format(sys.executable),
                encoding="utf-8",
            )
            binary.chmod(0o755)
            binaries[name] = binary
        project_binary_log = self.temporary / "project-binary-ran"
        project_binary = self.temporary / "project-controlled-nostdb"
        project_binary.write_text(
            "#!{}\nfrom pathlib import Path\n"
            "Path({!r}).write_text('executed')\n"
            "print('nostdb 0.0.1')\n".format(
                sys.executable, str(project_binary_log)
            ),
            encoding="utf-8",
        )
        project_binary.chmod(0o755)
        initialized = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "init",
            "--project",
            project,
            "--layout",
            "single",
            "--core-provider",
            "installed",
            "--core-binary",
            project_binary,
            "--module-id",
            "11111111-1111-1111-1111-111111111111",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertIn(
            'core_binary = "{}"'.format(project_binary),
            (project / "nostdb.toml").read_text(encoding="utf-8"),
        )
        path_directory = self.temporary / "path-bin"
        path_directory.mkdir()
        shutil.copy2(binaries["path"], path_directory / "nostdb")
        environment = os.environ.copy()
        environment["NOSTDB_BIN"] = str(binaries["environment"])
        environment["PATH"] = str(path_directory) + os.pathsep + environment.get("PATH", "")
        command = [
            sys.executable,
            str(ROOT / "scripts" / "nostdb_core.py"),
            "resolve",
            "--project",
            str(project),
        ]
        explicit = invoke(*command, "--binary", binaries["explicit"], env=environment)
        self.assertEqual(Path(explicit.stdout.strip()), binaries["explicit"].resolve())
        from_environment = invoke(*command, env=environment)
        self.assertEqual(
            Path(from_environment.stdout.strip()), binaries["environment"].resolve()
        )
        environment.pop("NOSTDB_BIN")
        from_path = invoke(*command, env=environment)
        self.assertEqual(from_path.returncode, 0, from_path.stderr)
        self.assertEqual(
            Path(from_path.stdout.strip()), (path_directory / "nostdb").resolve()
        )
        self.assertIn("ignoring untrusted skills.core_binary metadata", from_path.stderr)
        self.assertFalse(project_binary_log.exists())

        npx_log = self.temporary / "npx.log"
        fake_npx = path_directory / "npx"
        fake_npx.write_text(
            "#!{}\nfrom pathlib import Path\nPath({!r}).write_text('called')\n"
            .format(sys.executable, str(npx_log)),
            encoding="utf-8",
        )
        fake_npx.chmod(0o755)
        (path_directory / "nostdb").unlink()
        missing = invoke(*command, env=environment)
        self.assertEqual(missing.returncode, 3)
        self.assertIn("cannot locate nostdb 0.0.1", missing.stderr)
        self.assertIn("skills.core_binary is metadata only", missing.stderr)
        self.assertFalse(project_binary_log.exists())
        self.assertFalse(npx_log.exists())
        authorized = invoke(
            *command, "--binary", project_binary, env=environment
        )
        self.assertEqual(authorized.returncode, 0, authorized.stderr)
        self.assertEqual(Path(authorized.stdout.strip()), project_binary.resolve())
        self.assertEqual(project_binary_log.read_text(encoding="utf-8"), "executed")
        project_binary_log.unlink()
        config_path = project / "nostdb.toml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace(
                'core_provider = "installed"\n', ""
            ),
            encoding="utf-8",
        )
        legacy_missing = invoke(*command, env=environment)
        self.assertEqual(legacy_missing.returncode, 3)
        self.assertIn("cannot locate nostdb 0.0.1", legacy_missing.stderr)
        self.assertFalse(project_binary_log.exists())
        self.assertFalse(npx_log.exists())

    def test_npx_provider_is_pinned_and_preserves_process_behavior(self):
        project = self.temporary / "npx-project"
        initialized = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "init",
            "--project",
            project,
            "--layout",
            "single",
            "--core-provider",
            "auto",
            "--module-id",
            "11111111-1111-1111-1111-111111111111",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        tools = self.temporary / "npx-bin"
        tools.mkdir()
        npx_log = self.temporary / "npx.jsonl"
        signal_log = self.temporary / "signal.txt"
        fake_cli = self.temporary / "fake-cli.py"
        fake_cli.write_text(
            "#!{}\n"
            "import os, signal, sys, time\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('nostdb 0.0.1')\n"
            "elif sys.argv[1:] == ['forward', 'values with spaces', ';not-shell']:\n"
            "    print('forwarded stdout')\n"
            "    print('forwarded stderr', file=sys.stderr)\n"
            "    sys.exit(7)\n"
            "elif sys.argv[1:] == ['wait-signal']:\n"
            "    def stopped(signum, frame):\n"
            "        open(os.environ['SIGNAL_LOG'], 'w').write(str(signum))\n"
            "        sys.exit(0)\n"
            "    signal.signal(signal.SIGTERM, stopped)\n"
            "    print('ready', flush=True)\n"
            "    while True: time.sleep(0.05)\n"
            "else:\n"
            "    sys.exit(9)\n".format(sys.executable),
            encoding="utf-8",
        )
        fake_cli.chmod(0o755)
        fake_npx = tools / "npx"
        fake_npx.write_text(
            "#!{}\n"
            "import json, os, subprocess, sys\n"
            "with open(os.environ['NPX_LOG'], 'a') as output:\n"
            "    output.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:4] != ['--yes', '--package=@nostdb/cli@0.0.1', 'nostdb']:\n"
            "    sys.exit(97)\n"
            "sys.exit(subprocess.run([os.environ['FAKE_CLI']] + sys.argv[4:]).returncode)\n"
            .format(sys.executable),
            encoding="utf-8",
        )
        fake_npx.chmod(0o755)
        wrong_native = tools / "nostdb"
        wrong_native.write_text(
            "#!{}\nprint('nostdb 9.9.9')\n".format(sys.executable),
            encoding="utf-8",
        )
        wrong_native.chmod(0o755)
        configured = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "configure",
            "--project",
            project,
            "--core-provider",
            "npx",
        )
        self.assertEqual(configured.returncode, 0, configured.stderr)
        environment = os.environ.copy()
        environment.pop("NOSTDB_BIN", None)
        environment["PATH"] = str(tools)
        environment["NPX_LOG"] = str(npx_log)
        environment["FAKE_CLI"] = str(fake_cli)
        environment["SIGNAL_LOG"] = str(signal_log)
        base = [
            sys.executable,
            str(ROOT / "scripts" / "nostdb_core.py"),
        ]
        resolved = invoke(
            *base, "resolve", "--project", project, "--json", env=environment
        )
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        details = json.loads(resolved.stdout)
        self.assertEqual(details["provider"], "npx")
        self.assertIsNone(details["binary"])
        self.assertEqual(
            details["command"][1:],
            ["--yes", "--package=@nostdb/cli@0.0.1", "nostdb"],
        )
        explicit = invoke(
            *base,
            "resolve",
            "--project",
            project,
            "--binary",
            fake_cli,
            env=environment,
        )
        self.assertEqual(explicit.returncode, 3)
        self.assertIn("cannot be combined", explicit.stderr)
        forwarded = invoke(
            *base,
            "run",
            "--project",
            project,
            "--",
            "forward",
            "values with spaces",
            ";not-shell",
            env=environment,
        )
        self.assertEqual(forwarded.returncode, 7)
        self.assertEqual(forwarded.stdout, "forwarded stdout\n")
        self.assertEqual(forwarded.stderr, "forwarded stderr\n")
        calls = [json.loads(line) for line in npx_log.read_text().splitlines()]
        self.assertEqual(calls[-1][-3:], ["forward", "values with spaces", ";not-shell"])

        configured_auto = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "configure",
            "--project",
            project,
            "--core-provider",
            "auto",
        )
        self.assertEqual(configured_auto.returncode, 0, configured_auto.stderr)
        process = subprocess.Popen(
            base
            + [
                "run",
                "--project",
                str(project),
                "--binary",
                str(fake_cli),
                "--",
                "wait-signal",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        self.assertEqual(process.stdout.readline(), "ready\n")
        process.send_signal(signal.SIGTERM)
        process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(
            signal_log.read_text(encoding="utf-8"), str(int(signal.SIGTERM))
        )

    def test_windows_batch_shims_resolve_to_shell_free_node_vectors(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required for Windows shim resolution")

        prefix = self.temporary / "windows-prefix"
        native_shim = prefix / "nostdb.cmd"
        native_shim.parent.mkdir(parents=True)
        native_shim.write_text("@rem never execute through cmd.exe\n", encoding="utf-8")
        native_launcher = (
            prefix
            / "node_modules"
            / "@nostdb"
            / "cli"
            / "bin"
            / "nostdb.js"
        )
        native_launcher.parent.mkdir(parents=True)
        native_launcher.write_text("// fixture\n", encoding="utf-8")
        self.assertEqual(
            native_command(native_shim, windows=True),
            [str(Path(node).resolve()), str(native_launcher.resolve())],
        )

        npx_shim = prefix / "npx.cmd"
        npx_shim.write_text("@rem never execute through cmd.exe\n", encoding="utf-8")
        npx_cli = prefix / "node_modules" / "npm" / "bin" / "npx-cli.js"
        npx_cli.parent.mkdir(parents=True)
        npx_cli.write_text("// fixture\n", encoding="utf-8")
        self.assertEqual(
            npx_command(windows=True, located=str(npx_shim)),
            [str(Path(node).resolve()), str(npx_cli.resolve())],
        )

    def test_auto_does_not_hide_mismatch_and_reports_npx_failures(self):
        project = self.temporary / "auto-errors"
        tools = self.temporary / "auto-tools"
        tools.mkdir()
        npx_log = self.temporary / "error-npx.log"
        wrong = tools / "nostdb"
        wrong.write_text(
            "#!{}\nprint('nostdb 9.9.9')\n".format(sys.executable),
            encoding="utf-8",
        )
        wrong.chmod(0o755)
        fake_npx = tools / "npx"
        fake_npx.write_text(
            "#!{}\nfrom pathlib import Path\nimport os, sys\n"
            "Path(os.environ['NPX_LOG']).write_text('called')\n"
            "print('offline', file=sys.stderr)\nsys.exit(8)\n".format(sys.executable),
            encoding="utf-8",
        )
        fake_npx.chmod(0o755)
        initialized = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "init",
            "--project",
            project,
            "--layout",
            "single",
            "--core-provider",
            "auto",
            "--module-id",
            "11111111-1111-1111-1111-111111111111",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        environment = os.environ.copy()
        environment.pop("NOSTDB_BIN", None)
        environment["PATH"] = str(tools)
        environment["NPX_LOG"] = str(npx_log)
        command = [
            sys.executable,
            str(ROOT / "scripts" / "nostdb_core.py"),
            "resolve",
            "--project",
            str(project),
        ]
        mismatch = invoke(*command, env=environment)
        self.assertEqual(mismatch.returncode, 3)
        self.assertIn("found 9.9.9", mismatch.stderr)
        self.assertFalse(npx_log.exists())
        wrong.unlink()
        offline = invoke(*command, env=environment)
        self.assertEqual(offline.returncode, 3)
        self.assertIn("npm cache or network access", offline.stderr)
        self.assertTrue(npx_log.is_file())
        fake_npx.unlink()
        missing_npx = invoke(*command, env=environment)
        self.assertEqual(missing_npx.returncode, 3)
        self.assertIn("cannot locate npx", missing_npx.stderr)

    def test_provenance_is_deterministic_and_portable(self):
        source = FIXTURE / "inputs" / "people.md"
        arguments = (
            sys.executable,
            ROOT / "scripts" / "nostdb_provenance.py",
            "--project",
            ROOT,
            "--source",
            source,
            "--kind",
            "document",
            "--locator",
            "People paragraph 1",
        )
        first = invoke(*arguments)
        second = invoke(*arguments)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertIn('"sha256":"f7beae649542ed3be8a980148d89aad89cc7e8ad2f69d6f2d92a57ae0156b2bb"', first.stdout)
        self.assertIn('"source":"tests/fixtures/portable/inputs/people.md"', first.stdout)
        self.assertIn(first.stdout.strip(), (FIXTURE / "source.nostdb").read_text(encoding="utf-8"))
        code_arguments = list(arguments)
        code_arguments[code_arguments.index("document")] = "code"
        code_arguments[-1] = "people symbol"
        code = invoke(*code_arguments)
        self.assertEqual(code.returncode, 0, code.stderr)
        self.assertIn('"kind":"code"', code.stdout)
        changing = self.temporary / "changing.md"
        changing.write_text("first\n", encoding="utf-8")
        initial = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_provenance.py",
            "--project",
            self.temporary,
            "--source",
            changing,
            "--kind",
            "document",
            "--locator",
            "body",
        )
        initial_hash = json.loads(initial.stdout.split(" ", 2)[2])["sha256"]
        changing.write_text("second\n", encoding="utf-8")
        changed = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_provenance.py",
            "--project",
            self.temporary,
            "--source",
            changing,
            "--kind",
            "document",
            "--locator",
            "body",
            "--expected-sha256",
            initial_hash,
        )
        self.assertEqual(changed.returncode, 6)
        self.assertIn("source conflict", changed.stderr)

    def test_source_install_detects_conflicts_and_replaces_only_nostdb_text(self):
        target = self.temporary / "owner.nostdb"
        candidate = self.temporary / "candidate.txt"
        target.write_text("node old {}\n", encoding="utf-8")
        candidate.write_text("node new {}\n", encoding="utf-8")
        hashed = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_source.py",
            "hash",
            "--file",
            target,
        )
        self.assertEqual(hashed.returncode, 0, hashed.stderr)
        original_hash = hashed.stdout.strip()
        target.write_text("node concurrent {}\n", encoding="utf-8")
        conflict = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_source.py",
            "install",
            "--file",
            target,
            "--from",
            candidate,
            "--expected-sha256",
            original_hash,
        )
        self.assertEqual(conflict.returncode, 6)
        self.assertIn("source conflict", conflict.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "node concurrent {}\n")

        current = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_source.py",
            "hash",
            "--file",
            target,
        ).stdout.strip()
        lock = target.with_name("." + target.name + ".nostdb-lock")
        lock.write_text("busy\n", encoding="utf-8")
        locked = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_source.py",
            "install",
            "--file",
            target,
            "--from",
            candidate,
            "--expected-sha256",
            current,
        )
        self.assertEqual(locked.returncode, 6)
        self.assertEqual(target.read_text(encoding="utf-8"), "node concurrent {}\n")
        lock.unlink()
        stale_process = subprocess.Popen([sys.executable, "-c", "pass"])
        stale_process.wait()
        lock.write_text(
            json.dumps(
                {"host": __import__("socket").gethostname(), "pid": stale_process.pid}
            )
            + "\n",
            encoding="utf-8",
        )
        unlocked = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_source.py",
            "unlock",
            "--file",
            target,
        )
        self.assertEqual(unlocked.returncode, 0, unlocked.stderr)
        self.assertFalse(lock.exists())
        installed = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_source.py",
            "install",
            "--file",
            target,
            "--from",
            candidate,
            "--expected-sha256",
            current,
        )
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "node new {}\n")

    def test_source_install_revalidates_path_immediately_before_replace(self):
        target = self.temporary / "owner.nostdb"
        candidate = self.temporary / "candidate.txt"
        external = self.temporary / "external.nostdb"
        target.write_text("node original {}\n", encoding="utf-8")
        candidate.write_text("node candidate {}\n", encoding="utf-8")
        external.write_text("node external {}\n", encoding="utf-8")
        expected = source_digest(target.read_bytes())

        def replace_target():
            os.replace(str(external), str(target))

        with self.assertRaisesRegex(SourceError, "immediately before replacement"):
            source_install(
                target,
                candidate,
                expected,
                _before_replace=replace_target,
            )
        self.assertEqual(target.read_text(encoding="utf-8"), "node external {}\n")
        self.assertFalse(target.with_name("." + target.name + ".nostdb-lock").exists())
        self.assertEqual(list(target.parent.glob(".nostdb-source-*")), [])

    def test_adapters_install_identical_canonical_content(self):
        codex = self.temporary / "codex"
        claude = self.temporary / "claude"
        codex.mkdir()
        claude.mkdir()
        codex_result = invoke(sys.executable, ROOT / "adapters" / "codex" / "install.py", "--project", codex)
        claude_result = invoke(sys.executable, ROOT / "adapters" / "claude" / "install.py", "--project", claude)
        self.assertEqual(codex_result.returncode, 0, codex_result.stderr)
        self.assertEqual(claude_result.returncode, 0, claude_result.stderr)
        self.assertEqual(json.loads(codex_result.stdout)["skills"], list(SKILLS))
        self.assertEqual(json.loads(claude_result.stdout)["skills"], list(SKILLS))
        self.assertEqual(
            sorted(path.name for path in (codex / ".agents" / "skills").iterdir()),
            sorted(SKILLS),
        )
        self.assertEqual(
            sorted(path.name for path in (claude / ".claude" / "skills").iterdir()),
            sorted(SKILLS),
        )
        self.assertEqual(tree_hashes(codex / ".agents" / "skills"), tree_hashes(claude / ".claude" / "skills"))
        self.assertFalse((codex / ".agents" / "references").exists())
        self.assertFalse((codex / ".agents" / "scripts").exists())
        self.assertFalse((claude / ".claude" / "references").exists())
        self.assertFalse((claude / ".claude" / "scripts").exists())
        for name in SKILLS:
            self.assertEqual(
                tree_hashes(ROOT / "skills" / name),
                tree_hashes(codex / ".agents" / "skills" / name),
            )
        refused = invoke(sys.executable, ROOT / "adapters" / "codex" / "install.py", "--project", codex)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("refusing to replace", refused.stderr)
        unrelated = codex / ".agents" / "unrelated.md"
        unrelated.parent.mkdir(parents=True, exist_ok=True)
        unrelated.write_text("keep\n", encoding="utf-8")
        forced = invoke(
            sys.executable,
            ROOT / "adapters" / "codex" / "install.py",
            "--project",
            codex,
            "--force",
        )
        self.assertEqual(forced.returncode, 0, forced.stderr)
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep\n")

    def test_adapter_install_is_staged_and_rejects_symlink_boundaries(self):
        project = self.temporary / "atomic-adapter"
        project.mkdir()
        adapter_install(project, ".agents", "copy", False)
        markers = []
        for name in SKILLS:
            marker = project / ".agents" / "skills" / name / "retained.marker"
            marker.write_text("retain {}\n".format(name), encoding="utf-8")
            markers.append(marker)

        def fail_partial_copy(_source, destination, ignore=None):
            partial = Path(destination)
            partial.mkdir()
            (partial / "partial").write_text("incomplete\n", encoding="utf-8")
            raise OSError("injected copy failure")

        with mock.patch.object(
            adapter_module.shutil, "copytree", side_effect=fail_partial_copy
        ):
            with self.assertRaisesRegex(OSError, "injected copy failure"):
                adapter_install(project, ".agents", "copy", True)
        for name, marker in zip(SKILLS, markers):
            self.assertEqual(marker.read_text(encoding="utf-8"), "retain {}\n".format(name))
        self.assertEqual(
            list((project / ".agents" / "skills").glob(".nostdb-install-*")), []
        )

        escaped_project = self.temporary / "symlink-adapter"
        escaped_project.mkdir()
        external = self.temporary / "external-agent-root"
        external.mkdir()
        os.symlink(str(external), str(escaped_project / ".agents"), target_is_directory=True)
        refused = invoke(
            sys.executable,
            ROOT / "adapters" / "codex" / "install.py",
            "--project",
            escaped_project,
        )
        self.assertEqual(refused.returncode, 2)
        self.assertIn("symlink boundary", refused.stderr)
        self.assertEqual(list(external.iterdir()), [])

    def test_fixture_rejects_escaping_paths_before_creating_output(self):
        fixture = self.temporary / "unsafe-fixture"
        fixture.mkdir()
        (fixture / "source.nostdb").write_text("node safe {}\n", encoding="utf-8")
        (fixture / "fixture.json").write_text(
            json.dumps(
                {
                    "core_version": "0.0.1",
                    "layout": "single",
                    "module_id": "11111111-1111-1111-1111-111111111111",
                    "source_path": "../victim.nostdb",
                }
            ),
            encoding="utf-8",
        )
        output = self.temporary / "unsafe-output"
        victim = self.temporary / "victim.nostdb"
        victim.write_text("retain\n", encoding="utf-8")
        rejected = invoke(
            sys.executable,
            ROOT / "adapters" / "codex" / "run_fixture.py",
            "--fixture",
            fixture,
            "--output",
            output,
            "--core-provider",
            "auto",
        )
        self.assertEqual(rejected.returncode, 1)
        self.assertIn("normalized relative .nostdb path", rejected.stderr)
        self.assertFalse(output.exists())
        self.assertEqual(victim.read_text(encoding="utf-8"), "retain\n")

    def test_each_downloaded_skill_runs_without_repository_relative_support(self):
        installed = {}
        installation_roots = {
            "nostdb": self.temporary / "project-scope" / ".agents" / "skills",
            "nostdb-visualize": self.temporary / "global-scope" / ".codex" / "skills",
        }
        for name in SKILLS:
            destination = installation_roots[name] / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(ROOT / "skills" / name, destination)
            installed[name] = destination

        unrelated_cwd = self.temporary / "unrelated-working-directory"
        unrelated_cwd.mkdir()
        skill_entry = installed["nostdb"] / "scripts" / "nostdb_skill.py"
        helped = invoke(
            sys.executable,
            skill_entry,
            "help",
            cwd=unrelated_cwd,
        )
        self.assertEqual(helped.returncode, 0, helped.stderr)
        self.assertIn("Usage:\n  nostdb help\n  nostdb init", helped.stdout)
        self.assertIn("--core-provider auto", helped.stdout)
        self.assertFalse((unrelated_cwd / "nostdb.toml").exists())
        implicit_help = invoke(sys.executable, skill_entry, cwd=unrelated_cwd)
        self.assertEqual(implicit_help.stdout, helped.stdout)

        native = self.temporary / "nostdb-native"
        native.write_text(
            "#!{}\nimport sys\n"
            "print('nostdb 0.0.1') if sys.argv[1:] == ['--version'] else sys.exit(9)\n"
            .format(sys.executable),
            encoding="utf-8",
        )
        native.chmod(0o755)
        project = self.temporary / "standalone-project"
        initialized = invoke(
            sys.executable,
            skill_entry,
            "init",
            "--project",
            project,
            "--layout",
            "single",
            "--core-provider",
            "installed",
            "--core-binary",
            native,
            cwd=unrelated_cwd,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        native_environment = os.environ.copy()
        native_environment["NOSTDB_BIN"] = str(native)
        for name in SKILLS:
            resolved = invoke(
                sys.executable,
                installed[name] / "scripts" / "nostdb_core.py",
                "resolve",
                "--project",
                project,
                "--json",
                cwd=unrelated_cwd,
                env=native_environment,
            )
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            self.assertEqual(json.loads(resolved.stdout)["provider"], "native")

        npx_project = self.temporary / "standalone-npx-project"
        initialized = invoke(
            sys.executable,
            skill_entry,
            "init",
            "--project",
            npx_project,
            "--layout",
            "single",
            "--core-provider",
            "auto",
            cwd=unrelated_cwd,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        tools = self.temporary / "standalone-tools"
        tools.mkdir()
        npx_log = self.temporary / "standalone-npx.json"
        fake_npx = tools / "npx"
        fake_npx.write_text(
            "#!{}\nimport json, os, sys\n"
            "open(os.environ['NPX_LOG'], 'w').write(json.dumps(sys.argv[1:]))\n"
            "expected = ['--yes', '--package=@nostdb/cli@0.0.1', 'nostdb', '--version']\n"
            "print('nostdb 0.0.1') if sys.argv[1:] == expected else sys.exit(97)\n"
            .format(sys.executable),
            encoding="utf-8",
        )
        fake_npx.chmod(0o755)
        environment = os.environ.copy()
        environment.pop("NOSTDB_BIN", None)
        environment["PATH"] = str(tools)
        environment["NPX_LOG"] = str(npx_log)
        resolved = invoke(
            sys.executable,
            installed["nostdb-visualize"] / "scripts" / "nostdb_core.py",
            "resolve",
            "--project",
            npx_project,
            "--json",
            cwd=unrelated_cwd,
            env=environment,
        )
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        payload = json.loads(resolved.stdout)
        self.assertEqual(payload["provider"], "npx")
        self.assertEqual(
            payload["command"][1:],
            ["--yes", "--package=@nostdb/cli@0.0.1", "nostdb"],
        )
        self.assertEqual(
            json.loads(npx_log.read_text(encoding="utf-8")),
            ["--yes", "--package=@nostdb/cli@0.0.1", "nostdb", "--version"],
        )

    def test_visualization_wrapper_enforces_read_only_standalone_database(self):
        installed = self.temporary / "visualize" / "nostdb-visualize"
        installed.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "skills" / "nostdb-visualize", installed)
        wrapper = installed / "scripts" / "nostdb_core.py"
        database = self.temporary / "existing.ndb"
        database.write_bytes(b"opaque fixture")
        command_log = self.temporary / "visualize-commands.jsonl"
        binary = self.temporary / "visualize-nostdb"
        binary.write_text(
            "#!{}\n"
            "import json, os, sys\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('nostdb 0.0.1')\n"
            "else:\n"
            "    with open(os.environ['VISUALIZE_LOG'], 'a') as output:\n"
            "        output.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "    print('{{\"columns\":[],\"rows\":[]}}')\n".format(sys.executable),
            encoding="utf-8",
        )
        binary.chmod(0o755)
        environment = os.environ.copy()
        environment["VISUALIZE_LOG"] = str(command_log)
        base = [sys.executable, wrapper]

        resolved = invoke(
            *base,
            "resolve",
            "--binary",
            binary,
            "--database",
            database,
            "--json",
            env=environment,
        )
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        payload = json.loads(resolved.stdout)
        self.assertTrue(payload["read_only"])
        self.assertEqual(payload["database"], str(database.resolve()))
        self.assertFalse((database.parent / "nostdb.toml").exists())

        safe = invoke(
            *base,
            "run",
            "--binary",
            binary,
            "--database",
            database,
            "--",
            "query",
            "--read-only",
            "RETURN 'CREATE' AS text",
            "--format",
            "json",
            env=environment,
        )
        self.assertEqual(safe.returncode, 0, safe.stderr)
        forwarded = json.loads(command_log.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(forwarded[0], "query")
        self.assertIn(str(database.resolve()), forwarded)
        self.assertIn("--read-only", forwarded)
        self.assertNotIn("--project", forwarded)

        previous_log = command_log.read_text(encoding="utf-8")
        rejected = (
            ("query", "MATCH (n) RETURN n"),
            ("query", "--read-only", "--file", "query.cypher"),
            ("query", "--read-only", "--interactive"),
            ("query", "--read-only", "MATCH (n) RETURN n", "--server", "localhost"),
            ("sync",),
            ("database", "list"),
            ("query", "--read-only", "MATCH (n) RETURN n", "--project", "."),
        )
        for arguments in rejected:
            result = invoke(
                *base,
                "run",
                "--binary",
                binary,
                "--database",
                database,
                "--",
                *arguments,
                env=environment,
            )
            self.assertEqual(result.returncode, 3, (arguments, result.stderr))
        self.assertEqual(command_log.read_text(encoding="utf-8"), previous_log)

        project = self.temporary / "visualize-project"
        initialized = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "init",
            "--project",
            project,
            "--layout",
            "single",
            "--core-provider",
            "installed",
            "--module-id",
            "11111111-1111-1111-1111-111111111111",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        inspected = invoke(
            *base,
            "run",
            "--project",
            project,
            "--binary",
            binary,
            "--database",
            database,
            "--",
            "inspect",
            "--format",
            "json",
            env=environment,
        )
        self.assertEqual(inspected.returncode, 0, inspected.stderr)
        forwarded = json.loads(command_log.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(forwarded[0], "inspect")
        self.assertNotIn("--project", forwarded)

    def test_shared_fixture_has_equivalent_source_and_database_semantics(self):
        binary = os.environ.get("NOSTDB_TEST_BIN")
        if binary is None:
            suffix = ".exe" if os.name == "nt" else ""
            candidate = ROOT.parent / "nostdb-cli" / "target" / "debug" / ("nostdb" + suffix)
            if candidate.is_file():
                binary = str(candidate)
        if binary is None:
            self.skipTest("set NOSTDB_TEST_BIN to run adapter/Core conformance")
        outputs = {}
        for platform in ("codex", "claude"):
            result = invoke(
                sys.executable,
                ROOT / "adapters" / platform / "run_fixture.py",
                "--fixture",
                FIXTURE,
                "--output",
                self.temporary / (platform + "-fixture"),
                "--binary",
                binary,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs[platform] = json.loads(result.stdout)
        self.assertEqual(outputs["codex"], outputs["claude"])
        self.assertEqual(
            outputs["codex"],
            {
                "inspection": {
                    "columns": [
                        "ndb_format",
                        "schema_revision",
                        "generation",
                        "logical_checksum",
                        "source_managed",
                    ],
                    "rows": [[0, 2, 1, "fa1f44b5248e3bf0", True]],
                },
                "source_sha256": "774c768c5e5f34156bbcda0b9d15241fa8ad7e39f545998df0a241c716bb1171",
                "statistics": {
                    "columns": ["schemas", "nodes", "edges", "adjacency", "properties"],
                    "rows": [[2, 2, 1, 2, 3]],
                },
                "unresolved": {
                    "columns": ["kind", "internal_id", "identity", "state"],
                    "rows": [],
                },
                "warnings": {
                    "columns": ["module", "range", "code", "severity", "message"],
                    "rows": [],
                },
            },
        )
        codex_root = self.temporary / "codex-fixture"
        claude_root = self.temporary / "claude-fixture"
        self.assertEqual(
            (codex_root / ".nostdb" / "graph.nostdb").read_bytes(),
            (claude_root / ".nostdb" / "graph.nostdb").read_bytes(),
        )
        self.assertTrue((codex_root / "graph.ndb").is_file())
        self.assertTrue((claude_root / "graph.ndb").is_file())


if __name__ == "__main__":
    unittest.main()
