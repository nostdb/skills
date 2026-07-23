#!/usr/bin/env python3
"""Small dependency-free helpers for the versioned NostDB skill configuration."""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional


SECTION_RE = re.compile(r"^\s*\[([^]]+)]\s*(?:#.*)?$")
KEY_RE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*=\s*(.*?)\s*(?:#.*)?$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
CORE_PROVIDERS = ("auto", "installed", "npx")


class ConfigError(ValueError):
    """A deterministic skill-configuration error."""


def config_path(project: Path) -> Path:
    return project.resolve() / "nostdb.toml"


def read_text(project: Path) -> str:
    path = config_path(project)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError("cannot read {}: {}".format(path, error)) from error


def section_values(text: str, section: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    active = False
    for line in text.splitlines():
        header = SECTION_RE.match(line)
        if header:
            active = header.group(1) == section
            continue
        if not active:
            continue
        match = KEY_RE.match(line)
        if match:
            values[match.group(1)] = parse_string(match.group(2), match.group(1))
    return values


def parse_string(value: str, key: str) -> str:
    try:
        parsed, end = json.JSONDecoder().raw_decode(value)
    except json.JSONDecodeError as error:
        raise ConfigError("{}.{} must be a TOML basic string".format("skills", key)) from error
    if not isinstance(parsed, str):
        raise ConfigError("skills.{} must be a string".format(key))
    trailing = value[end:].strip()
    if trailing and not trailing.startswith("#"):
        raise ConfigError("invalid trailing value for skills.{}".format(key))
    return parsed


def skill_values(project: Path) -> Dict[str, str]:
    return section_values(read_text(project), "skills")


def require_core_version(project: Path) -> str:
    version = skill_values(project).get("core_version")
    if version is None:
        raise ConfigError("nostdb.toml is missing skills.core_version")
    return validate_core_version(version)


def validate_core_version(version: str) -> str:
    if not VERSION_RE.fullmatch(version):
        raise ConfigError("skills.core_version is not a valid pinned version: {}".format(version))
    return version


def validate_core_provider(provider: str) -> str:
    if provider not in CORE_PROVIDERS:
        raise ConfigError(
            "skills.core_provider must be one of: {}".format(
                ", ".join(CORE_PROVIDERS)
            )
        )
    return provider


def validate_database_path(value: str) -> str:
    path = Path(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or path.suffix != ".ndb"
    ):
        raise ConfigError("skills.database must be a normalized relative .ndb path")
    return value


def update_sections(text: str, updates: Dict[str, Dict[str, str]]) -> str:
    lines = text.splitlines()
    for section, values in updates.items():
        lines = _update_section(lines, section, values)
    return "\n".join(lines).rstrip() + "\n"


def _update_section(lines: List[str], section: str, values: Dict[str, str]) -> List[str]:
    start: Optional[int] = None
    end = len(lines)
    for index, line in enumerate(lines):
        header = SECTION_RE.match(line)
        if not header:
            continue
        if start is None and header.group(1) == section:
            start = index
            continue
        if start is not None:
            end = index
            break
    rendered = {key: '{} = {}'.format(key, json.dumps(value, ensure_ascii=False)) for key, value in values.items()}
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[{}]".format(section))
        lines.extend(rendered[key] for key in sorted(rendered))
        return lines
    found = set()
    for index in range(start + 1, end):
        match = KEY_RE.match(lines[index])
        if match and match.group(1) in rendered:
            key = match.group(1)
            lines[index] = rendered[key]
            found.add(key)
    additions = [rendered[key] for key in sorted(rendered) if key not in found]
    lines[end:end] = additions
    return lines


def atomic_write(path: Path, text: str) -> None:
    path = path.resolve()
    if path.name != "nostdb.toml":
        raise ConfigError("configuration helper may write only nostdb.toml")
    descriptor, temporary = tempfile.mkstemp(prefix=".nostdb-config-", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
        os.chmod(str(temporary_path), mode)
        os.replace(str(temporary_path), str(path))
    except BaseException:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def validate_module_id(value: str) -> str:
    import uuid

    try:
        parsed = uuid.UUID(value)
    except ValueError as error:
        raise ConfigError("invalid Stable Module ID: {}".format(value)) from error
    canonical = str(parsed)
    if canonical != value or parsed.int == 0:
        raise ConfigError("Stable Module ID must be nonzero canonical lowercase UUID text")
    return canonical


def layout_source(layout: str) -> str:
    paths = {
        "centralized": ".nostdb/graph.nostdb",
        "colocated": "graph.nostdb",
        "single": "project.nostdb",
    }
    try:
        return paths[layout]
    except KeyError as error:
        raise ConfigError("unknown source layout: {}".format(layout)) from error
