"""Model registry: load and validate `models.yaml`.

Security contract:
  - `models.yaml` is .gitignored; the committed template is `models.yaml.example`.
  - `api_key_env` must be the NAME of an environment variable, not the key itself.
  - The loader enforces this with a hard error if a field looks like an actual
    secret pasted in by mistake. This protects the user from accidentally
    committing `models.yaml` (e.g. if the gitignore is removed or a copy is
    shared) with a real key inside.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ModelRegistryError(ValueError):
    """Raised when `models.yaml` is missing fields, malformed, or contains a
    value that looks like an actual API key rather than an env-var name."""


@dataclass
class ModelEntry:
    name: str
    provider: str
    api_key_env: str


_REQUIRED_FIELDS = ("name", "provider", "api_key_env")

# POSIX-style env var name: starts with letter or underscore, then alphanum
# or underscore, all uppercase by convention. Anything that doesn't match
# this pattern is suspicious for an `api_key_env` field.
_ENV_VAR_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")

# Heuristic patterns common to leaked API keys. If the field value matches
# one of these, almost certainly a real key was pasted in by mistake.
_KEY_PREFIXES = ("sk-", "sk_", "ghp_", "gho_", "ghu_", "ghs_", "ghr_", "xai-")


def _looks_like_secret(value: str) -> bool:
    """Return True if `value` looks like an actual secret, not an env-var name."""
    if not value:
        return False
    if any(value.startswith(prefix) for prefix in _KEY_PREFIXES):
        return True
    if not _ENV_VAR_NAME.match(value):
        # Contains lowercase, hyphen, dot, slash, equals, etc. — env var names
        # are uppercase ASCII letters / digits / underscores only.
        return True
    if len(value) > 64:
        # Real env var names are short; long uppercase strings are suspicious.
        return True
    return False


def _validate_field_is_env_name(field_name: str, value: str, source: Path, idx: int) -> None:
    if _looks_like_secret(value):
        raise ModelRegistryError(
            f"{source}: models[{idx}].{field_name}={value!r} looks like an "
            "actual API key, not an env-var name. The `api_key_env` field must "
            "contain the NAME of an environment variable (e.g. "
            "`MINIMAX_API_KEY`), and the real key should be set in your shell "
            "via `export <NAME>=<key>`. See models.yaml.example."
        )


def load_models(path: Path) -> list[ModelEntry]:
    """Parse `models.yaml` and return a list of `ModelEntry`.

    Raises ModelRegistryError on missing keys, wrong types, or duplicate names.
    """
    if not path.is_file():
        raise ModelRegistryError(
            f"Model registry not found: {path}. "
            "Create a models.yaml file (see README) before running tests."
        )

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "models" not in raw:
        raise ModelRegistryError(
            f"{path}: top-level key `models` (a list) is required."
        )
    models_raw = raw["models"]
    if not isinstance(models_raw, list):
        raise ModelRegistryError(f"{path}: `models` must be a list.")

    entries: list[ModelEntry] = []
    seen_names: set[str] = set()
    for idx, item in enumerate(models_raw):
        if not isinstance(item, dict):
            raise ModelRegistryError(
                f"{path}: models[{idx}] must be a mapping, got {type(item).__name__}."
            )
        for field_name in _REQUIRED_FIELDS:
            if field_name not in item:
                raise ModelRegistryError(
                    f"{path}: models[{idx}] missing required field {field_name!r}."
                )
            if not isinstance(item[field_name], str) or not item[field_name].strip():
                raise ModelRegistryError(
                    f"{path}: models[{idx}].{field_name} must be a non-empty string."
                )
        # Security: `api_key_env` must be the NAME of an env var, not the key
        # itself. This guards against accidental key-in-yaml leaks.
        _validate_field_is_env_name("api_key_env", item["api_key_env"], path, idx)
        if item["name"] in seen_names:
            raise ModelRegistryError(
                f"{path}: duplicate model name {item['name']!r}."
            )
        seen_names.add(item["name"])
        entries.append(
            ModelEntry(
                name=item["name"],
                provider=item["provider"],
                api_key_env=item["api_key_env"],
            )
        )
    return entries


def resolve_api_key(entry: ModelEntry) -> str | None:
    """Return the API key for a model, or None if the env var is not set."""
    value = os.environ.get(entry.api_key_env)
    return value if value else None
