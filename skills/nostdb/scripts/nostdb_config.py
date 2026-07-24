#!/usr/bin/env python3
"""Small dependency-free helpers for the versioned NostDB skill configuration."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional


VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
CORE_PROVIDERS = ("auto", "installed", "npx")


class ConfigError(ValueError):
    """A deterministic skill-configuration error."""


class ConfigConflictError(ConfigError):
    """A configuration changed after it was read."""


def config_path(project: Path) -> Path:
    return project.resolve() / ".nostdb" / "settings.json"


def read_text(project: Path) -> str:
    path = config_path(project)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError("cannot read {}: {}".format(path, error)) from error


def project_document(project: Path) -> dict:
    """Read one object-root project configuration."""

    try:
        document = json.loads(read_text(project))
    except json.JSONDecodeError as error:
        raise ConfigError("settings.json is invalid JSON: {}".format(error)) from error
    if not isinstance(document, dict):
        raise ConfigError("settings.json must contain an object")
    return document


def configured_database(project: Path) -> str:
    """Return the required top-level project database root."""

    database = project_document(project).get("database")
    if not isinstance(database, dict):
        raise ConfigError("settings.json is missing database object")
    value = database.get("root")
    if not isinstance(value, str):
        raise ConfigError("settings.json is missing database.root")
    return validate_root_path(value)


def section_values(text: str, section: str) -> Dict[str, str]:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError("settings.json is invalid JSON: {}".format(error)) from error
    values = document.get(section)
    if not isinstance(values, dict):
        raise ConfigError("settings.json is missing object section {}".format(section))
    if any(not isinstance(value, str) for value in values.values()):
        raise ConfigError("settings.json section {} must contain strings".format(section))
    return dict(values)


def skill_values(project: Path) -> Dict[str, str]:
    return section_values(read_text(project), "skills")


def require_core_version(project: Path) -> str:
    version = skill_values(project).get("core_version")
    if version is None:
        raise ConfigError("settings.json is missing skills.core_version")
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


def validate_root_path(value: str) -> str:
    path = Path(value)
    if (
        path.name != value
        or path.suffix != ".nostdb"
        or value in ("", ".nostdb")
        or "/" in value
        or "\\" in value
    ):
        raise ConfigError("database.root must be a filename ending in .nostdb")
    return value


def update_sections(text: str, updates: Dict[str, Dict[str, str]]) -> str:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError("settings.json is invalid JSON: {}".format(error)) from error
    if not isinstance(document, dict):
        raise ConfigError("settings.json must contain an object")
    for section, values in updates.items():
        current = document.setdefault(section, {})
        if not isinstance(current, dict):
            raise ConfigError("settings.json section {} must be an object".format(section))
        current.update(values)
    return json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def update_values(text: str, updates: dict) -> str:
    """Update top-level values while preserving unrelated project metadata."""

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError("settings.json is invalid JSON: {}".format(error)) from error
    if not isinstance(document, dict):
        raise ConfigError("settings.json must contain an object")
    document.update(updates)
    return json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def atomic_write(path: Path, text: str, expected_text: Optional[str] = None) -> None:
    path = path.resolve()
    if path.name != "settings.json" or path.parent.name != ".nostdb":
        raise ConfigError(
            "configuration helper may write only .nostdb/settings.json"
        )
    descriptor, temporary = tempfile.mkstemp(prefix=".nost-config-", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
        os.chmod(str(temporary_path), mode)
        if expected_text is not None:
            expected_hash = hashlib.sha256(expected_text.encode("utf-8")).digest()
            try:
                current_hash = hashlib.sha256(path.read_bytes()).digest()
            except OSError as error:
                raise ConfigError(
                    "cannot revalidate {} before update: {}".format(path, error)
                ) from error
            if current_hash != expected_hash:
                raise ConfigConflictError(
                    "configuration changed during update; refusing to replace {}".format(
                        path
                    )
                )
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
