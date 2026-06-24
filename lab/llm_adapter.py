"""LLM adapter: thin wrapper around LiteLLM with a built-in mock provider.

Why this module exists:
  - The project tests need to run end-to-end without any real API key.
  - Every real call and every mock call goes through the same `complete()`
    function so the runner code paths stay identical in tests and production.
  - Mock responses are always prefixed with `[MOCK/<model>]` so a human reading
    a results file can never confuse canned output with a real model answer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from lab.config import DEFAULT_TEMPERATURE
from lab.model_registry import (
    ModelEntry,
    resolve_api_base,
    resolve_api_key,
    resolve_model_name,
)

try:
    import litellm  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - handled at runtime by MissingAPIKeyError path
    litellm = None  # type: ignore[assignment]


class MissingAPIKeyError(RuntimeError):
    """Raised when an API key is required but not present in the environment."""


@dataclass
class CompletionResult:
    text: str
    model: str
    raw: Any = None  # full provider response, useful for debugging


# Built-in mock responses. Keys match the names in models.yaml.
# Each response is intentionally distinguishable from a real model answer.
MOCK_RESPONSES: dict[str, str] = {
    "minimax3": (
        "[MOCK/minimax3] 你难受的点似乎不是面试结果，"
        "而是那个表情意味着什么。这种“潜台词识别”是 MiniMax 模型的优势。"
    ),
    "deepseek_v4": (
        "[MOCK/deepseek_v4] 别担心，你已经很优秀了。"
        "面试已经结束，结果不是你能控制的。下次会更好的。"
    ),
}


def _default_mock_response(model_name: str) -> str:
    """Fallback for any model name not in MOCK_RESPONSES."""
    return f"[MOCK/{model_name}] 这是来自 {model_name} 的模拟回答。"


def _resolve_mock_response(
    model_name: str,
    mock_responses: dict[str, str] | None,
) -> str:
    """Pick the canned text. Caller-provided dict overrides built-ins."""
    if mock_responses and model_name in mock_responses:
        return mock_responses[model_name]
    return MOCK_RESPONSES.get(model_name, _default_mock_response(model_name))


def _load_mock_file(path: Path) -> dict[str, str]:
    """Load a `--mock-file` YAML mapping {model_name: response_text}.

    The YAML can use either a string or a single-item list for the value.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Mock file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Mock file {path} must be a YAML mapping.")
    result: dict[str, str] = {}
    for model_name, value in raw.items():
        if isinstance(value, list):
            if not value:
                raise ValueError(
                    f"Mock file {path}: model {model_name!r} has an empty list."
                )
            result[str(model_name)] = str(value[0])
        else:
            result[str(model_name)] = str(value)
    return result


def _check_api_key(entry: ModelEntry) -> str:
    """Resolve the API key or raise MissingAPIKeyError."""
    key = resolve_api_key(entry)
    if not key:
        raise MissingAPIKeyError(
            f"Environment variable {entry.api_key_env!r} is not set for model "
            f"{entry.name!r}. Set it, or use --mock to run without API keys."
        )
    return key


def complete(
    model: ModelEntry,
    messages: list[dict[str, str]],
    *,
    mock: bool = False,
    mock_responses: dict[str, str] | None = None,
    mock_responses_file: Path | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
) -> CompletionResult:
    """Send a chat completion request to the configured model.

    Args:
        model: The model entry from the registry.
        messages: A list of `{"role": ..., "content": ...}` messages. The caller
            is responsible for session isolation — this function never reuses
            `messages` between invocations.
        mock: If True, return a canned response without contacting any provider.
        mock_responses: Optional override for MOCK_RESPONSES (model_name -> text).
        mock_responses_file: Optional path to a YAML file providing overrides.
        temperature: Sampling temperature passed to LiteLLM.

    Returns:
        A CompletionResult with the response text and the model name.

    Raises:
        MissingAPIKeyError: When mock=False and the required env var is unset.
    """
    if mock or mock_responses or mock_responses_file:
        if mock_responses_file is not None:
            mock_responses = _load_mock_file(mock_responses_file)
        text = _resolve_mock_response(model.name, mock_responses)
        return CompletionResult(text=text, model=model.name, raw={"mock": True})

    if litellm is None:  # pragma: no cover
        raise RuntimeError(
            "litellm is not installed. Run: pip install -r requirements.txt"
        )

    api_key = _check_api_key(model)

    # LiteLLM accepts provider-prefixed model names like "openai/gpt-4o".
    # `resolve_model_name` falls back to `model.name` if `model_name` is unset,
    # so a friendly alias (`minimax3`) can co-exist with a real API name
    # (`MiniMax-M3`) configured via the `model_name` field.
    litellm_model = f"{model.provider}/{resolve_model_name(model)}"

    # We MUST pass the resolved api_key explicitly: LiteLLM's default for
    # `provider: openai` (and any other provider) is to look up
    # `<PROVIDER>_API_KEY` from the environment. Since our env var name is
    # user-defined (e.g. `MINIMAX_API_KEY`), we'd get an "OPENAI_API_KEY
    # not set" error if we relied on the default.
    completion_kwargs: dict[str, Any] = {
        "model": litellm_model,
        "messages": messages,
        "temperature": temperature,
        "api_key": api_key,
    }
    # Optional: route the call to a custom API base URL (e.g. an OpenAI-
    # compatible vendor hosted on a different host). When the env var is
    # unset, we don't pass `api_base` and LiteLLM uses its built-in default.
    api_base = resolve_api_base(model)
    if api_base:
        completion_kwargs["api_base"] = api_base

    response = litellm.completion(**completion_kwargs)
    text = response.choices[0].message.content or ""
    return CompletionResult(text=text, model=model.name, raw=response)
