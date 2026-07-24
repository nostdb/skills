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
from nostdb_config import ConfigConflictError, atomic_write  # noqa: E402
from nostdb_core import native_command, npx_command  # noqa: E402
from nostdb_provider import installed_command  # noqa: E402
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


def write_project_settings(
    project,
    *,
    core_version="0.0.3",
    core_provider="auto",
    core_binary=None,
    root="root.nostdb",
):
    storage = Path(project) / ".nostdb"
    storage.mkdir(parents=True)
    skills = {
        "core_provider": core_provider,
        "core_version": core_version,
    }
    if core_binary is not None:
        skills["core_binary"] = str(core_binary)
    document = {
        "version": 1,
        "database": {"links": [], "root": root},
        "source": {"enabled": False, "version": 1},
        "skills": skills,
    }
    settings = storage / "settings.json"
    settings.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return settings


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

    def test_configuration_update_rejects_external_edit_conflicts(self):
        project = self.temporary / "config-conflict"
        configuration = project / ".nostdb" / "settings.json"
        configuration.parent.mkdir(parents=True)
        current = '{"version":1,"database":{"root":"root.nostdb"},"source":{"version":1,"enabled":false}}\n'
        configuration.write_text(current, encoding="utf-8")

        with self.assertRaisesRegex(ConfigConflictError, "configuration changed"):
            atomic_write(
                configuration,
                '{"version":1,"database":{"root":"root.nostdb"},"source":{"version":1,"enabled":false},"skills":{}}\n',
                expected_text='{"version":1,"database":{"root":"root.nostdb"},"source":{"version":1,"enabled":true}}\n',
            )

        self.assertEqual(configuration.read_text(encoding="utf-8"), current)
        self.assertEqual(list(configuration.parent.glob(".nost-config-*")), [])

    def test_public_wrapper_uses_only_native_initialization(self):
        source = (ROOT / "scripts" / "nostdb_skill.py").read_text(encoding="utf-8")
        self.assertNotIn("_supports_native_init", source)
        self.assertNotIn("_initialize_with_", source)
        project = self.temporary / "no-python-init"
        rejected = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "init",
            "--src",
            project,
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertFalse(project.exists())

    def test_project_configuration_updates_the_versioned_settings(self):
        project = self.temporary / "configured"
        settings_path = write_project_settings(project)
        document = json.loads(settings_path.read_text(encoding="utf-8"))
        document["source"]["validation"] = {"mode": "strict"}
        settings_path.write_text(json.dumps(document) + "\n", encoding="utf-8")
        result = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "configure",
            "--src",
            project,
            "--core-version",
            "0.1.1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = settings_path.read_text(encoding="utf-8")
        document = json.loads(settings)
        self.assertEqual(document["source"]["validation"], {"mode": "strict"})
        self.assertEqual(document["database"]["root"], "root.nostdb")
        self.assertFalse(document["source"]["enabled"])
        self.assertEqual(document["skills"]["core_version"], "0.1.1")

        enabled = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "configure",
            "--src",
            project,
            "--source-enabled",
            "true",
        )
        self.assertEqual(enabled.returncode, 0, enabled.stderr)
        document = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertTrue(document["source"]["enabled"])

    def test_public_init_creates_database_without_materializing_source(self):
        binary = os.environ.get("NOSTDB_TEST_BIN")
        if binary is None:
            suffix = ".exe" if os.name == "nt" else ""
            candidate = ROOT.parent / "nostdb-cli" / "target" / "debug" / ("nostdb" + suffix)
            if candidate.is_file():
                binary = str(candidate)
        if binary is None:
            self.skipTest("set NOSTDB_TEST_BIN to run public initialization")
        project = self.temporary / "public-init"
        environment = os.environ.copy()
        environment["NOSTDB_BIN"] = binary
        initialized = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_skill.py",
            "init",
            "--src",
            project,
            "--core-provider",
            "installed",
            env=environment,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        payload = json.loads(initialized.stdout)
        self.assertEqual(payload["root"], "root.nostdb")
        self.assertTrue((project / ".nostdb").is_dir())
        self.assertTrue((project / ".nostdb" / "root.nostdb").is_file())
        self.assertFalse((project / ".nostdb" / "graph.nost").exists())
        document = json.loads(
            (project / ".nostdb" / "settings.json").read_text(encoding="utf-8")
        )
        self.assertFalse(document["source"]["enabled"])
        self.assertEqual(document["database"]["root"], "root.nostdb")
        self.assertEqual(document["database"]["links"], [])
        self.assertNotIn("modules", document["source"])

    def test_public_update_discovers_and_synchronizes_nested_projects(self):
        binary = os.environ.get("NOSTDB_TEST_BIN")
        if binary is None:
            self.skipTest("set NOSTDB_TEST_BIN to run public update")
        environment = os.environ.copy()
        environment["NOSTDB_BIN"] = binary
        parent = self.temporary / "linked-parent"
        child = parent / "module-a"
        for project, extra in (
            (parent, []),
            (child, ["--root", "module.nostdb"]),
        ):
            initialized = invoke(
                sys.executable,
                ROOT / "scripts" / "nostdb_skill.py",
                "init",
                "--src",
                project,
                "--core-provider",
                "installed",
                *extra,
                env=environment,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)

        updated = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_skill.py",
            "update",
            "--src",
            parent,
            env=environment,
        )
        self.assertEqual(updated.returncode, 0, updated.stderr)
        payload = json.loads(updated.stdout)
        self.assertEqual(
            payload["links"],
            [{"project": "module-a", "root": "module.nostdb"}],
        )
        self.assertEqual(len(payload["updated"]["rows"]), 2)
        settings = json.loads(
            (parent / ".nostdb" / "settings.json").read_text(encoding="utf-8")
        )
        self.assertEqual(settings["database"]["links"], payload["links"])
        self.assertTrue((child / ".nostdb" / "module.nostdb").is_file())
        self.assertTrue((parent / ".nostdb" / "root.nostdb").is_file())

    def test_link_discovery_does_not_follow_a_symlinked_storage_directory(self):
        parent = self.temporary / "symlink-parent"
        external = self.temporary / "external-project"
        for project in (parent, external):
            write_project_settings(project, core_provider="installed")
            (project / ".nostdb" / "root.nostdb").write_bytes(b"opaque")
        linked = parent / "linked"
        linked.mkdir()
        try:
            (linked / ".nostdb").symlink_to(
                external / ".nostdb",
                target_is_directory=True,
            )
        except OSError as error:
            self.skipTest("directory symlinks are unavailable: {}".format(error))

        refreshed = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "refresh",
            "--src",
            parent,
        )
        self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
        self.assertEqual(json.loads(refreshed.stdout)["links"], [])

    def test_remove_deletes_only_scoped_nostdb_artifacts(self):
        src = self.temporary / "remove"
        src.mkdir()
        (src / "unrelated.txt").write_text("preserve\n", encoding="utf-8")
        (src / "code").mkdir()
        (src / "code" / "keep.txt").write_text("keep\n", encoding="utf-8")
        write_project_settings(src)
        for relative in (
            ".nostdb/graph.nost",
            ".nostdb/root.nostdb",
            ".nostdb/root.nostdb-wal",
            ".nostdb/root.nostdb-shm",
            ".nostdb/root.nostdb-journal",
            ".nostdb/root.nostdb.lock",
            ".nostdb/.nost-source-orphan",
            "unmanaged.nost",
            "code/module.nost",
            "graph.nostdb",
        ):
            target = src / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fixture")

        dry_run = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_skill.py",
            "remove",
            "--src",
            src,
            "--dry-run",
        )
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        preview = json.loads(dry_run.stdout)
        self.assertTrue(preview["dry_run"])
        self.assertEqual(preview["removed"], [])
        self.assertEqual(preview["targets"], [".nostdb"])
        self.assertNotIn("unmanaged.nost", preview["targets"])
        self.assertNotIn("code/module.nost", preview["targets"])
        self.assertTrue((src / "graph.nostdb").exists())

        removed = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_skill.py",
            "remove",
            "--src",
            src,
        )
        self.assertEqual(removed.returncode, 0, removed.stderr)
        payload = json.loads(removed.stdout)
        self.assertFalse(payload["dry_run"])
        self.assertEqual(payload["removed"], preview["targets"])
        self.assertEqual((src / "unrelated.txt").read_text(encoding="utf-8"), "preserve\n")
        self.assertEqual((src / "code" / "keep.txt").read_text(encoding="utf-8"), "keep\n")
        self.assertEqual((src / "unmanaged.nost").read_bytes(), b"fixture")
        self.assertEqual((src / "code" / "module.nost").read_bytes(), b"fixture")
        self.assertTrue((src / "graph.nostdb").is_file())
        self.assertFalse((src / ".nostdb").exists())

        repeated = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_skill.py",
            "remove",
            "--src",
            src,
        )
        self.assertEqual(repeated.returncode, 3)
        self.assertIn("without a regular", repeated.stderr)

    @unittest.skipIf(os.name == "nt", "POSIX lock probe")
    def test_remove_refuses_symlinks_and_open_database_locks(self):
        import fcntl

        src = self.temporary / "remove-guards"
        write_project_settings(src)
        external = self.temporary / "external"
        external.mkdir()
        os.symlink(
            str(external),
            str(src / ".nostdb" / "external"),
            target_is_directory=True,
        )
        symlinked = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "remove",
            "--src",
            src,
        )
        self.assertEqual(symlinked.returncode, 3)
        self.assertIn("symlink boundary", symlinked.stderr)
        self.assertTrue((src / ".nostdb" / "settings.json").exists())
        (src / ".nostdb" / "external").unlink()

        database = src / ".nostdb" / "root.nostdb"
        lock_path = src / ".nostdb" / "root.nostdb.lock"
        database.write_bytes(b"opaque")
        with lock_path.open("w+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = invoke(
                sys.executable,
                ROOT / "scripts" / "nostdb_project.py",
                "remove",
                "--src",
                src,
            )
            self.assertEqual(locked.returncode, 3)
            self.assertIn("open NostDB database", locked.stderr)
        self.assertTrue(database.exists())
        self.assertTrue((src / ".nostdb" / "settings.json").exists())

    def test_core_version_mismatch_is_explicit(self):
        project = self.temporary / "version"
        fake = self.temporary / "nostdb-fake"
        fake.write_text("#!/usr/bin/env python3\nprint('nostdb 9.9.9')\n", encoding="utf-8")
        fake.chmod(0o755)
        write_project_settings(project, core_binary=fake)
        mismatch = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_core.py",
            "resolve",
            "--src",
            project,
            "--binary",
            fake,
        )
        self.assertEqual(mismatch.returncode, 3)
        self.assertIn("Core version mismatch: expected 0.0.3", mismatch.stderr)
        self.assertIn("found 9.9.9", mismatch.stderr)

        configured = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_project.py",
            "configure",
            "--src",
            project,
            "--core-version",
            "9.9.9",
        )
        self.assertEqual(configured.returncode, 0, configured.stderr)
        matched = invoke(
            sys.executable,
            ROOT / "scripts" / "nostdb_core.py",
            "resolve",
            "--src",
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
            "--src",
            project,
            "--binary",
            fake,
            "--json",
        )
        self.assertEqual(json.loads(details.stdout)["database"], "root.nostdb")
        self.assertEqual(json.loads(details.stdout)["provider"], "native")

    def test_native_provider_trust_boundary_and_installed_only_policy(self):
        project = self.temporary / "providers"
        binaries = {}
        for name in ("explicit", "environment", "path"):
            binary = self.temporary / ("nostdb-" + name)
            binary.write_text(
                "#!{}\nimport sys\nprint('nostdb 0.0.3')\n".format(sys.executable),
                encoding="utf-8",
            )
            binary.chmod(0o755)
            binaries[name] = binary
        project_binary_log = self.temporary / "project-binary-ran"
        project_binary = self.temporary / "project-controlled-nostdb"
        project_binary.write_text(
            "#!{}\nfrom pathlib import Path\n"
            "Path({!r}).write_text('executed')\n"
            "print('nostdb 0.0.3')\n".format(
                sys.executable, str(project_binary_log)
            ),
            encoding="utf-8",
        )
        project_binary.chmod(0o755)
        write_project_settings(
            project,
            core_provider="installed",
            core_binary=project_binary,
        )
        self.assertEqual(
            json.loads(
                (project / ".nostdb" / "settings.json").read_text(encoding="utf-8")
            )["skills"]["core_binary"],
            str(project_binary),
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
            "--src",
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
        self.assertEqual(from_path.stdout.strip(), "nostdb")
        from_path_json = invoke(*command, "--json", env=environment)
        self.assertEqual(from_path_json.returncode, 0, from_path_json.stderr)
        self.assertEqual(json.loads(from_path_json.stdout)["binary"], "nostdb")
        self.assertEqual(json.loads(from_path_json.stdout)["command"], ["nostdb"])
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
        self.assertIn("cannot execute nostdb 0.0.3", missing.stderr)
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
        config_path = project / ".nostdb" / "settings.json"
        document = json.loads(config_path.read_text(encoding="utf-8"))
        del document["skills"]["core_provider"]
        config_path.write_text(json.dumps(document) + "\n", encoding="utf-8")
        missing_policy = invoke(*command, env=environment)
        self.assertEqual(missing_policy.returncode, 3)
        self.assertIn("missing skills.core_provider", missing_policy.stderr)
        self.assertFalse(project_binary_log.exists())
        self.assertFalse(npx_log.exists())

    def test_npx_provider_is_pinned_and_preserves_process_behavior(self):
        project = self.temporary / "npx-project"
        write_project_settings(project)
        tools = self.temporary / "npx-bin"
        tools.mkdir()
        npx_log = self.temporary / "npx.jsonl"
        signal_log = self.temporary / "signal.txt"
        fake_cli = self.temporary / "fake-cli.py"
        fake_cli.write_text(
            "#!{}\n"
            "import os, signal, sys, time\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('nostdb 0.0.3')\n"
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
            "if sys.argv[1:4] != ['--yes', '--package=@nostdb/cli@0.0.3', 'nostdb']:\n"
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
            "--src",
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
            *base, "resolve", "--src", project, "--json", env=environment
        )
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        details = json.loads(resolved.stdout)
        self.assertEqual(details["provider"], "npx")
        self.assertIsNone(details["binary"])
        self.assertEqual(
            details["command"][1:],
            ["--yes", "--package=@nostdb/cli@0.0.3", "nostdb"],
        )
        explicit = invoke(
            *base,
            "resolve",
            "--src",
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
            "--src",
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
            "--src",
            project,
            "--core-provider",
            "auto",
        )
        self.assertEqual(configured_auto.returncode, 0, configured_auto.stderr)
        process = subprocess.Popen(
            base
            + [
                "run",
                "--src",
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

    def test_posix_installed_detection_uses_the_command_without_path_lookup(self):
        with mock.patch(
            "nostdb_provider.shutil.which",
            side_effect=AssertionError("POSIX detection must not resolve nostdb"),
        ):
            self.assertEqual(installed_command(windows=False), ["nostdb"])

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
        write_project_settings(project)
        environment = os.environ.copy()
        environment.pop("NOSTDB_BIN", None)
        environment["PATH"] = str(tools)
        environment["NPX_LOG"] = str(npx_log)
        command = [
            sys.executable,
            str(ROOT / "scripts" / "nostdb_core.py"),
            "resolve",
            "--src",
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
            "--src",
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
        self.assertIn(first.stdout.strip(), (FIXTURE / "source.nost").read_text(encoding="utf-8"))
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
            "--src",
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
            "--src",
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
        target = self.temporary / "owner.nost"
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
        lock = target.with_name("." + target.name + ".nost-lock")
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
        target = self.temporary / "owner.nost"
        candidate = self.temporary / "candidate.txt"
        external = self.temporary / "external.nost"
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
        self.assertFalse(target.with_name("." + target.name + ".nost-lock").exists())
        self.assertEqual(list(target.parent.glob(".nost-source-*")), [])

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
            list((project / ".agents" / "skills").glob(".nost-install-*")), []
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
        (fixture / "source.nost").write_text("node safe {}\n", encoding="utf-8")
        (fixture / "fixture.json").write_text(
            json.dumps(
                {
                    "core_version": "0.0.3",
                    "module_id": "11111111-1111-1111-1111-111111111111",
                    "source_path": "../victim.nost",
                }
            ),
            encoding="utf-8",
        )
        output = self.temporary / "unsafe-output"
        victim = self.temporary / "victim.nost"
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
        self.assertIn("normalized relative .nost path", rejected.stderr)
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
        skill_instructions = (installed["nostdb"] / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Respond directly from this file without running Python", skill_instructions)
        self.assertIn("Initialization defaults to Core `0.0.3`", skill_instructions)
        self.assertNotIn("nostdb_skill.py help", skill_instructions)
        self.assertFalse((unrelated_cwd / ".nostdb").exists())

        native = self.temporary / "nostdb-native"
        native.write_text(
            "#!{}\nimport json, pathlib, sys\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('nostdb 0.0.3')\n"
            "elif sys.argv[1:2] == ['init']:\n"
            "    project = pathlib.Path(sys.argv[sys.argv.index('--project') + 1])\n"
            "    root = sys.argv[sys.argv.index('--database') + 1]\n"
            "    storage = project / '.nostdb'\n"
            "    storage.mkdir(parents=True, exist_ok=True)\n"
            "    (storage / 'settings.json').write_text(json.dumps({{\n"
            "        'version': 1,\n"
            "        'database': {{'root': root, 'links': []}},\n"
            "        'source': {{'version': 1, 'enabled': False}}\n"
            "    }}))\n"
            "    (storage / root).write_bytes(b'core-created fixture')\n"
            "    print('{{\"columns\":[],\"rows\":[]}}')\n"
            "else:\n"
            "    sys.exit(9)\n".format(sys.executable),
            encoding="utf-8",
        )
        native.chmod(0o755)
        project = self.temporary / "standalone-project"
        initialized = invoke(
            sys.executable,
            skill_entry,
            "init",
            "--src",
            project,
            "--core-provider",
            "installed",
            "--core-binary",
            native,
            cwd=unrelated_cwd,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertEqual(
            json.loads(
                (project / ".nostdb" / "settings.json").read_text()
            )["skills"]["core_provider"],
            "installed",
        )
        self.assertTrue((project / ".nostdb" / "root.nostdb").is_file())

        native_environment = os.environ.copy()
        native_environment["NOSTDB_BIN"] = str(native)
        for name in SKILLS:
            resolved = invoke(
                sys.executable,
                installed[name] / "scripts" / "nostdb_core.py",
                "resolve",
                "--src",
                project,
                "--json",
                cwd=unrelated_cwd,
                env=native_environment,
            )
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            self.assertEqual(json.loads(resolved.stdout)["provider"], "native")

        npx_project = self.temporary / "standalone-npx-project"
        write_project_settings(npx_project)
        tools = self.temporary / "standalone-tools"
        tools.mkdir()
        npx_log = self.temporary / "standalone-npx.json"
        fake_npx = tools / "npx"
        fake_npx.write_text(
            "#!{}\nimport json, os, sys\n"
            "open(os.environ['NPX_LOG'], 'w').write(json.dumps(sys.argv[1:]))\n"
            "expected = ['--yes', '--package=@nostdb/cli@0.0.3', 'nostdb', '--version']\n"
            "print('nostdb 0.0.3') if sys.argv[1:] == expected else sys.exit(97)\n"
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
            "--src",
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
            ["--yes", "--package=@nostdb/cli@0.0.3", "nostdb"],
        )
        self.assertEqual(
            json.loads(npx_log.read_text(encoding="utf-8")),
            ["--yes", "--package=@nostdb/cli@0.0.3", "nostdb", "--version"],
        )

    def test_visualization_wrapper_enforces_read_only_standalone_database(self):
        installed = self.temporary / "visualize" / "nostdb-visualize"
        installed.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "skills" / "nostdb-visualize", installed)
        wrapper = installed / "scripts" / "nostdb_core.py"
        database = self.temporary / "existing.nostdb"
        database.write_bytes(b"opaque fixture")
        command_log = self.temporary / "visualize-commands.jsonl"
        binary = self.temporary / "visualize-nostdb"
        binary.write_text(
            "#!{}\n"
            "import json, os, sys\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('nostdb 0.0.3')\n"
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
        self.assertFalse((database.parent / "settings.json").exists())

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
        write_project_settings(project, core_provider="installed")
        inspected = invoke(
            *base,
            "run",
            "--src",
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
                        "source_enabled",
                    ],
                    "rows": [[0, 3, 1, True]],
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
            (codex_root / ".nostdb" / "graph.nost").read_bytes(),
            (claude_root / ".nostdb" / "graph.nost").read_bytes(),
        )
        self.assertTrue((codex_root / ".nostdb" / "root.nostdb").is_file())
        self.assertTrue((claude_root / ".nostdb" / "root.nostdb").is_file())


if __name__ == "__main__":
    unittest.main()
