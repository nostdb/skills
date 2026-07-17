#!/usr/bin/env python3
"""Dependency-free structural and safety verifier for the portable Skills."""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

from install_adapter import SKILL_NAMES


ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^]]+]\(([^)]+)\)")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class VerificationError(RuntimeError):
    """A repository conformance failure."""


def portable_files() -> List[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    )


def frontmatter(path: Path) -> Dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise VerificationError("{} has no YAML frontmatter".format(path))
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise VerificationError("{} has unterminated frontmatter".format(path)) from error
    values = {}
    for line in lines[1:end]:
        if ":" not in line:
            raise VerificationError("{} has malformed frontmatter".format(path))
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    if set(values) != {"name", "description"}:
        raise VerificationError("{} frontmatter must contain only name and description".format(path))
    return values


def verify_skills() -> int:
    discovered = sorted(path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md"))
    if discovered != sorted(SKILL_NAMES):
        raise VerificationError("canonical Skill set does not match the six registered names")
    for name in SKILL_NAMES:
        path = ROOT / "skills" / name / "SKILL.md"
        values = frontmatter(path)
        if values["name"] != name or not NAME_RE.fullmatch(name):
            raise VerificationError("invalid Skill name in {}".format(path))
        if len(values["description"]) < 80:
            raise VerificationError("{} description does not explain its triggers".format(path))
        text = path.read_text(encoding="utf-8")
        if len(text.splitlines()) > 500 or "Not yet implemented" in text:
            raise VerificationError("{} is not a concise implemented Skill".format(path))
        if any(marker in text for marker in (".agents/", ".claude/", "Codex adapter", "Claude adapter")):
            raise VerificationError("platform-specific behavior leaked into {}".format(path))
    return len(discovered)


def verify_links() -> int:
    count = 0
    for path in portable_files():
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = match.group(1).split("#", 1)[0]
            if not target or "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                raise VerificationError("broken link in {}: {}".format(path, target))
            count += 1
    return count


def verify_python_safety() -> int:
    count = 0
    forbidden_imports = {"sqlite3", "rusqlite", "nostos_parser", "nostos_storage"}
    write_calls = {"open", "write_bytes", "write_text", "copy", "copyfile", "replace", "rename"}
    for path in sorted(list((ROOT / "scripts").glob("*.py")) + list((ROOT / "adapters").glob("*/*.py"))):
        if path.resolve() == Path(__file__).resolve():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name.split(".", 1)[0] for alias in node.names] if isinstance(node, ast.Import) else [(node.module or "").split(".", 1)[0]]
                if forbidden_imports.intersection(names):
                    raise VerificationError("{} imports a forbidden parser/storage library".format(path))
            if isinstance(node, ast.Call):
                function = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
                if function in write_calls:
                    for argument in node.args:
                        if isinstance(argument, ast.Constant) and isinstance(argument.value, str) and argument.value.endswith(".ndb"):
                            raise VerificationError("{} directly writes an .ndb path".format(path))
        for line in path.read_text(encoding="utf-8").splitlines():
            if ".ndb" in line and any(token in line for token in ("write_bytes", "write_text", "copyfile", "sqlite")):
                raise VerificationError("{} contains a direct .ndb write".format(path))
        count += 1
    return count


def verify_fixture() -> int:
    fixture = ROOT / "tests" / "fixtures" / "portable"
    manifest = json.loads((fixture / "fixture.json").read_text(encoding="utf-8"))
    required = {"core_version", "layout", "module_id", "source_path"}
    if set(manifest) != required or manifest["layout"] not in {"centralized", "colocated", "single"}:
        raise VerificationError("portable fixture manifest is invalid")
    source = (fixture / "source.nostos").read_text(encoding="utf-8")
    if "@provenance" not in source:
        raise VerificationError("portable fixture does not cover provenance")
    return 1


def verify_format() -> int:
    count = 0
    for path in portable_files():
        if path.name == "LICENSE" or path.suffix not in {".md", ".py", ".json", ".nostos"} and path.name not in {".gitignore"}:
            continue
        data = path.read_bytes()
        if b"\r" in data or (data and not data.endswith(b"\n")):
            raise VerificationError("{} must use LF and end with a newline".format(path))
        text = data.decode("utf-8")
        if any(line.endswith((" ", "\t")) for line in text.splitlines()):
            raise VerificationError("{} has trailing whitespace".format(path))
        if path.suffix == ".json":
            parsed = json.loads(text)
            canonical = json.dumps(parsed, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            if text != canonical:
                raise VerificationError("{} is not canonical JSON".format(path))
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format-check", action="store_true")
    args = parser.parse_args()
    try:
        formatted = verify_format()
        if args.format_check:
            print("format: {} portable files".format(formatted))
            return 0
        skills = verify_skills()
        links = verify_links()
        scripts = verify_python_safety()
        fixtures = verify_fixture()
        print(
            "skills: {}; scripts: {}; links: {}; fixtures: {}; format files: {}".format(
                skills, scripts, links, fixtures, formatted
            )
        )
        return 0
    except (OSError, UnicodeError, ValueError, SyntaxError, VerificationError) as error:
        print("verify-skills: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
