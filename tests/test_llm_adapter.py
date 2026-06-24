"""Tests for `lab.llm_adapter.complete`.

These tests verify that `complete()` correctly passes `api_base` and uses
`model_name` (when configured) when calling the underlying LiteLLM client.
The LiteLLM client itself is mocked so no real API call is made.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lab.llm_adapter import CompletionResult, complete
from lab.model_registry import ModelEntry


def _make_fake_response(text: str) -> Any:
    """Build a MagicMock that quacks like a LiteLLM completion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = text
    return response


class TestCompleteWithApiBase:
    def test_passes_api_base_and_key_when_env_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_KEY", "secret-key-123")
        monkeypatch.setenv("CUSTOM_BASE", "https://api.example.com/v1")
        entry = ModelEntry(
            name="m",
            provider="openai",
            api_key_env="TEST_KEY",
            api_base_env="CUSTOM_BASE",
        )
        fake = _make_fake_response("hello")
        with patch("lab.llm_adapter.litellm.completion", return_value=fake) as m:
            result = complete(
                entry, [{"role": "user", "content": "hi"}]
            )
        # The LiteLLM call should have received both api_base and api_key
        # explicitly — relying on env-var lookup would fail for user-defined
        # api_key_env names like `MINIMAX_API_KEY`.
        assert m.call_args is not None
        kwargs = m.call_args.kwargs
        assert kwargs["api_base"] == "https://api.example.com/v1"
        assert kwargs["api_key"] == "secret-key-123"
        assert kwargs["model"] == "openai/m"
        assert isinstance(result, CompletionResult)
        assert result.text == "hello"

    def test_passes_api_key_even_without_api_base(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_KEY", "k")
        entry = ModelEntry(name="m", provider="openai", api_key_env="TEST_KEY")
        fake = _make_fake_response("ok")
        with patch("lab.llm_adapter.litellm.completion", return_value=fake) as m:
            complete(entry, [{"role": "user", "content": "hi"}])
        kwargs = m.call_args.kwargs
        assert "api_base" not in kwargs
        assert kwargs["api_key"] == "k"

    def test_omits_api_base_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_KEY", "k")
        monkeypatch.delenv("CUSTOM_BASE", raising=False)
        entry = ModelEntry(
            name="m",
            provider="openai",
            api_key_env="TEST_KEY",
            api_base_env="CUSTOM_BASE",
        )
        fake = _make_fake_response("ok")
        with patch("lab.llm_adapter.litellm.completion", return_value=fake) as m:
            complete(entry, [{"role": "user", "content": "hi"}])
        kwargs = m.call_args.kwargs
        assert "api_base" not in kwargs
        assert kwargs["api_key"] == "k"


class TestCompleteWithModelName:
    def test_uses_model_name_when_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_KEY", "secret")
        entry = ModelEntry(
            name="friendly_alias",
            provider="openai",
            api_key_env="TEST_KEY",
            model_name="real-api-name",
        )
        fake = _make_fake_response("ok")
        with patch("lab.llm_adapter.litellm.completion", return_value=fake) as m:
            result = complete(entry, [{"role": "user", "content": "hi"}])
        # The LiteLLM model string should be "openai/real-api-name", NOT
        # "openai/friendly_alias" — the alias is for humans, not the API.
        assert m.call_args.kwargs["model"] == "openai/real-api-name"
        # But the result.model (the human-facing name) should be the alias.
        assert result.model == "friendly_alias"

    def test_falls_back_to_name_when_model_name_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_KEY", "secret")
        entry = ModelEntry(name="just-a-name", provider="openai", api_key_env="TEST_KEY")
        fake = _make_fake_response("ok")
        with patch("lab.llm_adapter.litellm.completion", return_value=fake) as m:
            complete(entry, [{"role": "user", "content": "hi"}])
        assert m.call_args.kwargs["model"] == "openai/just-a-name"


class TestCompleteMock:
    """The mock path is unchanged: it never touches LiteLLM."""

    def test_mock_returns_canned_text(self) -> None:
        entry = ModelEntry(name="m", provider="p", api_key_env="UNUSED")
        result = complete(entry, [{"role": "user", "content": "hi"}], mock=True)
        assert result.text.startswith("[MOCK/m]")
        assert result.model == "m"

    def test_mock_does_not_call_litellm(self) -> None:
        entry = ModelEntry(name="m", provider="p", api_key_env="UNUSED")
        with patch("lab.llm_adapter.litellm.completion") as m:
            complete(entry, [{"role": "user", "content": "hi"}], mock=True)
            m.assert_not_called()


class TestCompleteRequiresApiKey:
    def test_real_call_without_key_raises(self) -> None:
        # No --mock, no env var, no api_base set up.
        entry = ModelEntry(
            name="m",
            provider="openai",
            api_key_env="DEFINITELY_NOT_SET_FOR_REAL_KEY_XYZ",
        )
        with pytest.raises(Exception, match="not set"):
            complete(entry, [{"role": "user", "content": "hi"}])
