"""Model registry: load and validate `models.yaml`."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ModelRegistryError(ValueError):
    """Raised when `models.yaml` is missing fields or malformed."""


@dataclass
class ModelEntry:
    name: str
    provider: str
    api_key_env: str


_REQUIRED_FIELDS = ("name", "provider", "api_key_env")


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
