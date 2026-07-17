import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "portable"
SKILLS = (
    "nostos-orchestrator",
    "nostos-core",
    "nostos-ingest",
    "nostos-schema",
    "nostos-explore",
    "nostos-visualize",
)


def invoke(*arguments, cwd=None):
    return subprocess.run(
        [str(argument) for argument in arguments],
        cwd=str(cwd) if cwd else None,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def tree_hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.temporary = Path(tempfile.mkdtemp(prefix="nostos-skills-test-"))

    def tearDown(self):
        shutil.rmtree(self.temporary)

    def test_repository_verifier_and_portable_frontmatter(self):
        result = invoke(sys.executable, ROOT / "scripts" / "verify_skills.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skills: 6", result.stdout)
        for name in SKILLS:
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            header = text.split("---", 2)[1].strip().splitlines()
            self.assertEqual({line.split(":", 1)[0] for line in header}, {"name", "description"})
            self.assertIn("name: " + name, header)

    def test_layout_and_core_pin_are_persisted_without_losing_configuration(self):
        for layout, source in (
            ("centralized", ".nostos/graph.nostos"),
            ("colocated", "graph.nostos"),
            ("single", "project.nostos"),
        ):
            project = self.temporary / layout
            result = invoke(
                sys.executable,
                ROOT / "scripts" / "nostos_project.py",
                "init",
                "--project",
                project,
                "--layout",
                layout,
                "--core-version",
                "0.1.0",
                "--module-id",
                "11111111-1111-1111-1111-111111111111",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["source"], source)
            self.assertTrue((project / source).is_file())
            config = (project / "nostos.toml").read_text(encoding="utf-8")
            self.assertIn('layout = "{}"'.format(layout), config)
            self.assertIn('core_version = "0.1.0"', config)
            self.assertIn('database = "graph.ndb"', config)
            self.assertIn('"{}" = "11111111-1111-1111-1111-111111111111"'.format(source), config)

        project = self.temporary / "single"
        config_path = project / "nostos.toml"
        config_path.write_text(config_path.read_text(encoding="utf-8") + "# retained\n", encoding="utf-8")
        result = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_project.py",
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
        self.assertIn('"project.nostos" = "11111111-1111-1111-1111-111111111111"', config)

        occupied = self.temporary / "occupied"
        occupied.mkdir()
        (occupied / "unrelated.txt").write_text("preserve\n", encoding="utf-8")
        refused = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_project.py",
            "init",
            "--project",
            occupied,
            "--layout",
            "single",
        )
        self.assertEqual(refused.returncode, 3)
        self.assertIn("nonempty directory", refused.stderr)
        self.assertFalse((occupied / "nostos.toml").exists())
        allowed = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_project.py",
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
        fake = self.temporary / "nostos-fake"
        fake.write_text("#!/usr/bin/env python3\nprint('nostos 9.9.9')\n", encoding="utf-8")
        fake.chmod(0o755)
        initialized = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_project.py",
            "init",
            "--project",
            project,
            "--layout",
            "single",
            "--core-version",
            "0.1.0",
            "--core-binary",
            fake,
            "--module-id",
            "11111111-1111-1111-1111-111111111111",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        mismatch = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_core.py",
            "resolve",
            "--project",
            project,
        )
        self.assertEqual(mismatch.returncode, 3)
        self.assertIn("Core version mismatch: expected 0.1.0", mismatch.stderr)
        self.assertIn("found 9.9.9", mismatch.stderr)

        configured = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_project.py",
            "configure",
            "--project",
            project,
            "--core-version",
            "9.9.9",
        )
        self.assertEqual(configured.returncode, 0, configured.stderr)
        matched = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_core.py",
            "resolve",
            "--project",
            project,
        )
        self.assertEqual(matched.returncode, 0, matched.stderr)
        self.assertEqual(Path(matched.stdout.strip()), fake.resolve())
        details = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_core.py",
            "resolve",
            "--project",
            project,
            "--json",
        )
        self.assertEqual(json.loads(details.stdout)["database"], "graph.ndb")

    def test_provenance_is_deterministic_and_portable(self):
        source = FIXTURE / "inputs" / "people.md"
        arguments = (
            sys.executable,
            ROOT / "scripts" / "nostos_provenance.py",
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
        self.assertIn('"sha256":"5429cda0d1e0f74e014792b2a51ce7089e2c68aa0e193fe9cbbd3d9cbde449f0"', first.stdout)
        self.assertIn('"source":"tests/fixtures/portable/inputs/people.md"', first.stdout)
        self.assertIn(first.stdout.strip(), (FIXTURE / "source.nostos").read_text(encoding="utf-8"))
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
            ROOT / "scripts" / "nostos_provenance.py",
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
            ROOT / "scripts" / "nostos_provenance.py",
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

    def test_source_install_detects_conflicts_and_replaces_only_nostos_text(self):
        target = self.temporary / "owner.nostos"
        candidate = self.temporary / "candidate.txt"
        target.write_text("node old {}\n", encoding="utf-8")
        candidate.write_text("node new {}\n", encoding="utf-8")
        hashed = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_source.py",
            "hash",
            "--file",
            target,
        )
        self.assertEqual(hashed.returncode, 0, hashed.stderr)
        original_hash = hashed.stdout.strip()
        target.write_text("node concurrent {}\n", encoding="utf-8")
        conflict = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_source.py",
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
            ROOT / "scripts" / "nostos_source.py",
            "hash",
            "--file",
            target,
        ).stdout.strip()
        lock = target.with_name("." + target.name + ".nostos-lock")
        lock.write_text("busy\n", encoding="utf-8")
        locked = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_source.py",
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
            ROOT / "scripts" / "nostos_source.py",
            "unlock",
            "--file",
            target,
        )
        self.assertEqual(unlocked.returncode, 0, unlocked.stderr)
        self.assertFalse(lock.exists())
        installed = invoke(
            sys.executable,
            ROOT / "scripts" / "nostos_source.py",
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

    def test_adapters_install_identical_canonical_content(self):
        codex = self.temporary / "codex"
        claude = self.temporary / "claude"
        codex.mkdir()
        claude.mkdir()
        codex_result = invoke(sys.executable, ROOT / "adapters" / "codex" / "install.py", "--project", codex)
        claude_result = invoke(sys.executable, ROOT / "adapters" / "claude" / "install.py", "--project", claude)
        self.assertEqual(codex_result.returncode, 0, codex_result.stderr)
        self.assertEqual(claude_result.returncode, 0, claude_result.stderr)
        self.assertEqual(tree_hashes(codex / ".agents" / "skills"), tree_hashes(claude / ".claude" / "skills"))
        self.assertEqual(tree_hashes(codex / ".agents" / "references"), tree_hashes(claude / ".claude" / "references"))
        self.assertEqual(tree_hashes(codex / ".agents" / "scripts"), tree_hashes(claude / ".claude" / "scripts"))
        for name in SKILLS:
            self.assertEqual(
                (ROOT / "skills" / name / "SKILL.md").read_bytes(),
                (codex / ".agents" / "skills" / name / "SKILL.md").read_bytes(),
            )
        refused = invoke(sys.executable, ROOT / "adapters" / "codex" / "install.py", "--project", codex)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("refusing to replace", refused.stderr)
        unrelated = codex / ".agents" / "references" / "unrelated.md"
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

    def test_shared_fixture_has_equivalent_source_and_database_semantics(self):
        binary = os.environ.get("NOSTOS_TEST_BIN")
        if binary is None:
            suffix = ".exe" if os.name == "nt" else ""
            candidate = ROOT.parent / "nostos-cli" / "target" / "debug" / ("nostos" + suffix)
            if candidate.is_file():
                binary = str(candidate)
        if binary is None:
            self.skipTest("set NOSTOS_TEST_BIN to run adapter/Core conformance")
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
                    "rows": [[0, 2, 1, "dc0a5ff3cd3d2835", True]],
                },
                "source_sha256": "7b0043a3cbe900043aaedca9715a036204fb6fe2a754245115e6214bc8983bb7",
                "statistics": {
                    "columns": ["schemas", "nodes", "edges", "adjacency", "properties"],
                    "rows": [[2, 2, 1, 2, 3]],
                },
            },
        )
        codex_root = self.temporary / "codex-fixture"
        claude_root = self.temporary / "claude-fixture"
        self.assertEqual(
            (codex_root / ".nostos" / "graph.nostos").read_bytes(),
            (claude_root / ".nostos" / "graph.nostos").read_bytes(),
        )
        self.assertTrue((codex_root / "graph.ndb").is_file())
        self.assertTrue((claude_root / "graph.ndb").is_file())


if __name__ == "__main__":
    unittest.main()
