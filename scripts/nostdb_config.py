#!/usr/bin/env python3
"""Small dependency-free helpers for the versioned NostDB skill configuration."""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict


VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
CORE_PROVIDERS = ("auto", "installed", "npx")


class ConfigError(ValueError):
    """A deterministic skill-configuration error."""


def config_path(project: Path) -> Path:
    return project.resolve() / "nostdb.json"


def read_text(project: Path) -> str:
    path = config_path(project)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError("cannot read {}: {}".format(path, error)) from error


def section_values(text: str, section: str) -> Dict[str, str]:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError("nostdb.json is invalid JSON: {}".format(error)) from error
    values = document.get(section)
    if not isinstance(values, dict):
        raise ConfigError("nostdb.json is missing object section {}".format(section))
    if any(not isinstance(value, str) for value in values.values()):
        raise ConfigError("nostdb.json section {} must contain strings".format(section))
    return dict(values)


def skill_values(project: Path) -> Dict[str, str]:
    return section_values(read_text(project), "skills")


def require_core_version(project: Path) -> str:
    version = skill_values(project).get("core_version")
    if version is None:
        raise ConfigError("nostdb.json is missing skills.core_version")
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
        or path.suffix != ".nostdb"
    ):
        raise ConfigError("skills.database must be a normalized relative .nostdb path")
    return value


def update_sections(text: str, updates: Dict[str, Dict[str, str]]) -> str:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError("nostdb.json is invalid JSON: {}".format(error)) from error
    if not isinstance(document, dict):
        raise ConfigError("nostdb.json must contain an object")
    for section, values in updates.items():
        current = document.setdefault(section, {})
        if not isinstance(current, dict):
            raise ConfigError("nostdb.json section {} must be an object".format(section))
        current.update(values)
    return json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def atomic_write(path: Path, text: str) -> None:
    path = path.resolve()
    if path.name != "nostdb.json":
        raise ConfigError("configuration helper may write only nostdb.json")
    descriptor, temporary = tempfile.mkstemp(prefix=".nost-config-", dir=str(path.parent))
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
        "centralized": ".nost/graph.nost",
        "colocated": "graph.nost",
        "single": "project.nost",
    }
    try:
        return paths[layout]
    except KeyError as error:
        raise ConfigError("unknown source layout: {}".format(layout)) from error
