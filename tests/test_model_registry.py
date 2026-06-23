"""Tests for `lab.model_registry`."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lab.model_registry import (
    ModelEntry,
    ModelRegistryError,
    load_models,
    resolve_api_key,
)


class TestLoadModels:
    def test_basic_yaml(self, tmp_path: Path, sample_models_yaml: str) -> None:
        path = tmp_path / "models.yaml"
        path.write_text(sample_models_yaml, encoding="utf-8")
        models = load_models(path)
        assert len(models) == 2
        assert models[0] == ModelEntry(
            name="minimax3", provider="minimax", api_key_env="MINIMAX_API_KEY"
        )
        assert models[1] == ModelEntry(
            name="deepseek_v4", provider="deepseek", api_key_env="DEEPSEEK_API_KEY"
        )

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ModelRegistryError, match="not found"):
            load_models(tmp_path / "absent.yaml")

    def test_missing_top_level_models_key(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text("something_else: []\n", encoding="utf-8")
        with pytest.raises(ModelRegistryError, match="`models`"):
            load_models(tmp_path / "models.yaml")

    def test_models_must_be_list(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text("models: not-a-list\n", encoding="utf-8")
        with pytest.raises(ModelRegistryError, match="must be a list"):
            load_models(tmp_path / "models.yaml")

    def test_missing_required_field(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n  - name: foo\n    provider: bar\n", encoding="utf-8"
        )
        with pytest.raises(ModelRegistryError, match="api_key_env"):
            load_models(tmp_path / "models.yaml")

    def test_duplicate_name_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: dup\n    provider: p\n    api_key_env: E\n"
            "  - name: dup\n    provider: p\n    api_key_env: E\n",
            encoding="utf-8",
        )
        with pytest.raises(ModelRegistryError, match="duplicate model name"):
            load_models(tmp_path / "models.yaml")

    def test_empty_string_field_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n  - name: ''\n    provider: p\n    api_key_env: E\n",
            encoding="utf-8",
        )
        with pytest.raises(ModelRegistryError, match="non-empty string"):
            load_models(tmp_path / "models.yaml")


class TestResolveApiKey:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_KEY", "secret123")
        entry = ModelEntry(name="m", provider="p", api_key_env="TEST_KEY")
        assert resolve_api_key(entry) == "secret123"

    def test_returns_none_when_unset(self) -> None:
        entry = ModelEntry(name="m", provider="p", api_key_env="DEFINITELY_NOT_SET_XYZ")
        assert resolve_api_key(entry) is None

    def test_returns_none_for_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_KEY", "")
        entry = ModelEntry(name="m", provider="p", api_key_env="TEST_KEY")
        assert resolve_api_key(entry) is None
