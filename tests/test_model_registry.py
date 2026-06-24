"""Tests for `lab.model_registry`."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lab.model_registry import (
    ModelEntry,
    ModelRegistryError,
    load_models,
    resolve_api_base,
    resolve_api_key,
    resolve_model_name,
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


class TestSecretDetection:
    """Security check: `api_key_env` must be an env-var NAME, not a real key."""

    def test_real_openai_style_key_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: gpt4o\n"
            "    provider: openai\n"
            "    api_key_env: sk-abc123def456ghi789jkl012mno345pqr678stu901\n",
            encoding="utf-8",
        )
        with pytest.raises(ModelRegistryError, match="looks like an actual API key"):
            load_models(tmp_path / "models.yaml")

    def test_anthropic_style_key_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: claude\n"
            "    provider: anthropic\n"
            "    api_key_env: sk-ant-api03-verylongstringthatshouldnotbehere\n",
            encoding="utf-8",
        )
        with pytest.raises(ModelRegistryError, match="looks like an actual API key"):
            load_models(tmp_path / "models.yaml")

    def test_github_pat_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: m\n"
            "    provider: p\n"
            "    api_key_env: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n",
            encoding="utf-8",
        )
        with pytest.raises(ModelRegistryError, match="looks like an actual API key"):
            load_models(tmp_path / "models.yaml")

    def test_lowercase_value_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: m\n"
            "    provider: p\n"
            "    api_key_env: my_secret_key_value\n",
            encoding="utf-8",
        )
        with pytest.raises(ModelRegistryError, match="looks like an actual API key"):
            load_models(tmp_path / "models.yaml")

    def test_hyphenated_value_rejected(self, tmp_path: Path) -> None:
        # An env var name can't contain hyphens. Anything with a hyphen is
        # almost certainly a token or a value, not a name.
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: m\n"
            "    provider: p\n"
            "    api_key_env: MY-SECRET-KEY\n",
            encoding="utf-8",
        )
        with pytest.raises(ModelRegistryError, match="looks like an actual API key"):
            load_models(tmp_path / "models.yaml")

    def test_valid_env_var_name_accepted(self, tmp_path: Path) -> None:
        # Sanity: legitimate env-var names still pass.
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: minimax3\n"
            "    provider: minimax\n"
            "    api_key_env: MINIMAX_API_KEY_V2\n",
            encoding="utf-8",
        )
        models = load_models(tmp_path / "models.yaml")
        assert models[0].api_key_env == "MINIMAX_API_KEY_V2"

    def test_name_field_not_subject_to_check(self, tmp_path: Path) -> None:
        # The `name` field legitimately contains lowercase (e.g. "gpt-4o").
        # Only `api_key_env` is checked.
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: gpt-4o\n"
            "    provider: openai\n"
            "    api_key_env: OPENAI_API_KEY\n",
            encoding="utf-8",
        )
        models = load_models(tmp_path / "models.yaml")
        assert models[0].name == "gpt-4o"


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


class TestOptionalFields:
    """model_name and api_base_env are optional; both default to None."""

    def test_model_name_optional(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n  - name: m\n    provider: p\n    api_key_env: K\n",
            encoding="utf-8",
        )
        models = load_models(tmp_path / "models.yaml")
        assert models[0].model_name is None
        assert models[0].api_base_env is None

    def test_model_name_loaded(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: friendly_alias\n"
            "    provider: openai\n"
            "    api_key_env: K\n"
            "    model_name: gpt-4o\n",
            encoding="utf-8",
        )
        models = load_models(tmp_path / "models.yaml")
        assert models[0].model_name == "gpt-4o"

    def test_api_base_env_loaded(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: m\n"
            "    provider: openai\n"
            "    api_key_env: K\n"
            "    api_base_env: CUSTOM_BASE\n",
            encoding="utf-8",
        )
        models = load_models(tmp_path / "models.yaml")
        assert models[0].api_base_env == "CUSTOM_BASE"

    def test_api_base_env_must_be_env_name_not_url(self, tmp_path: Path) -> None:
        # If someone pastes a raw URL into api_base_env, refuse it.
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: m\n"
            "    provider: openai\n"
            "    api_key_env: K\n"
            "    api_base_env: https://api.example.com/v1\n",
            encoding="utf-8",
        )
        with pytest.raises(ModelRegistryError, match="looks like an actual API key"):
            load_models(tmp_path / "models.yaml")

    def test_api_base_env_empty_string_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "models.yaml").write_text(
            "models:\n"
            "  - name: m\n"
            "    provider: openai\n"
            "    api_key_env: K\n"
            "    api_base_env: ''\n",
            encoding="utf-8",
        )
        with pytest.raises(ModelRegistryError, match="non-empty string"):
            load_models(tmp_path / "models.yaml")


class TestResolveApiBase:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CUSTOM_BASE", "https://api.example.com/v1")
        entry = ModelEntry(
            name="m", provider="p", api_key_env="K", api_base_env="CUSTOM_BASE"
        )
        assert resolve_api_base(entry) == "https://api.example.com/v1"

    def test_returns_none_when_unset(self) -> None:
        entry = ModelEntry(
            name="m",
            provider="p",
            api_key_env="K",
            api_base_env="DEFINITELY_NOT_SET_XYZ",
        )
        assert resolve_api_base(entry) is None

    def test_returns_none_when_field_missing(self) -> None:
        entry = ModelEntry(name="m", provider="p", api_key_env="K")
        assert resolve_api_base(entry) is None

    def test_returns_none_for_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CUSTOM_BASE", "")
        entry = ModelEntry(
            name="m", provider="p", api_key_env="K", api_base_env="CUSTOM_BASE"
        )
        assert resolve_api_base(entry) is None


class TestResolveModelName:
    def test_falls_back_to_name_when_model_name_unset(self) -> None:
        entry = ModelEntry(name="friendly", provider="p", api_key_env="K")
        assert resolve_model_name(entry) == "friendly"

    def test_uses_model_name_when_set(self) -> None:
        entry = ModelEntry(
            name="friendly", provider="p", api_key_env="K", model_name="real-name"
        )
        assert resolve_model_name(entry) == "real-name"

    def test_empty_model_name_falls_back_to_name(self) -> None:
        # Defensive: even if model_name is somehow an empty string, fall back.
        # (The loader rejects empty strings, but this guards future code.)
        entry = ModelEntry(
            name="friendly", provider="p", api_key_env="K", model_name=""
        )
        assert resolve_model_name(entry) == "friendly"
