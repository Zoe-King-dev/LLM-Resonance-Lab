"""Shared test fixtures: tmp paths, mock model registry, mock responses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lab.config import Paths


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Paths:
    """A fresh `Paths` rooted at a temp dir, with all expected subdirs created."""
    (tmp_path / "cases").mkdir()
    (tmp_path / "marathons").mkdir()
    p = Paths.from_root(tmp_path)
    p.results.mkdir(exist_ok=True)
    p.blind.mkdir(exist_ok=True)
    p.evaluation.mkdir(exist_ok=True)
    p.journal.mkdir(exist_ok=True)
    return p


@pytest.fixture
def sample_case_md() -> str:
    return (
        "---\n"
        'id: case_001\n'
        "category: understanding\n"
        "tags:\n"
        "  - emotion\n"
        "  - interview\n"
        "description: 测试模型是否能发现潜台词\n"
        "---\n"
        "\n"
        "我今天面试结束之后特别难受。\n"
        "我知道自己发挥得不差。\n"
        "但我还是一直在想面试官那个奇怪的表情。\n"
    )


@pytest.fixture
def sample_models_yaml() -> str:
    return (
        "models:\n"
        "  - name: minimax3\n"
        "    provider: minimax\n"
        "    api_key_env: MINIMAX_API_KEY\n"
        "  - name: deepseek_v4\n"
        "    provider: deepseek\n"
        "    api_key_env: DEEPSEEK_API_KEY\n"
    )


@pytest.fixture
def mock_responses() -> dict[str, str]:
    """Canonical mock responses for tests that need a full set."""
    return {
        "minimax3": "[MOCK/minimax3] 你难受的点似乎不是面试结果，而是那个表情意味着什么。",
        "deepseek_v4": "[MOCK/deepseek_v4] 别担心，你已经很优秀了。下次会更好的。",
    }
