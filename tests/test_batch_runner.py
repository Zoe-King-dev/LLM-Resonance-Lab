"""Tests for `lab.batch_runner` (A 组: isolated sessions)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from lab.batch_runner import BatchSummary, run_batch
from lab.case_loader import Case
from lab.model_registry import ModelEntry


def _case(cid: str, body: str = "测试问题") -> Case:
    return Case(id=cid, category="understanding", tags=[], description="", body=body)


def _model(name: str = "minimax3") -> ModelEntry:
    return ModelEntry(name=name, provider="mock", api_key_env="MOCK_KEY")


class TestRunBatchSignature:
    """Design guard: run_batch must NOT accept a `messages` parameter."""

    def test_no_messages_parameter(self) -> None:
        sig = inspect.signature(run_batch)
        assert "messages" not in sig.parameters, (
            "run_batch must not accept a `messages` parameter — that would "
            "let callers share session state across cases and break A 组 isolation."
        )


class TestRunBatch:
    def test_writes_per_case_per_model(self, tmp_path: Path) -> None:
        cases = [_case("case_001"), _case("case_002")]
        models = [_model("minimax3"), _model("deepseek_v4")]
        out = tmp_path / "results"

        summary = run_batch(cases, models, out_dir=out, mock=True)

        assert summary.cases_run == 4  # 2 cases * 2 models
        assert summary.skipped == 0
        # Each case dir has exactly the configured model files
        for cid in ("case_001", "case_002"):
            case_dir = out / cid
            assert case_dir.is_dir()
            assert (case_dir / "minimax3.md").is_file()
            assert (case_dir / "deepseek_v4.md").is_file()

    def test_output_contains_frontmatter_and_response(
        self, tmp_path: Path
    ) -> None:
        cases = [_case("case_001", body="面试结束之后我很难受")]
        out = tmp_path / "results"
        run_batch(cases, [_model()], out_dir=out, mock=True)

        text = (out / "case_001" / "minimax3.md").read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert "case_id: case_001" in text
        assert "model: minimax3" in text
        assert "面试结束之后我很难受" in text  # prompt is in frontmatter
        assert "[MOCK/minimax3]" in text  # response body

    def test_custom_mock_responses_override(self, tmp_path: Path) -> None:
        cases = [_case("case_001")]
        models = [_model("custom_model")]
        out = tmp_path / "results"
        run_batch(
            cases,
            models,
            out_dir=out,
            mock=True,
            mock_responses={"custom_model": "完全自定义的回答"},
        )
        text = (out / "case_001" / "custom_model.md").read_text(encoding="utf-8")
        assert "完全自定义的回答" in text

    def test_no_cases_returns_empty_summary(self, tmp_path: Path) -> None:
        out = tmp_path / "results"
        summary = run_batch([], [_model()], out_dir=out, mock=True)
        assert summary.cases_run == 0
        assert not (out / "case_001").exists()

    def test_no_models_returns_empty_summary(self, tmp_path: Path) -> None:
        out = tmp_path / "results"
        summary = run_batch([_case("case_001")], [], out_dir=out, mock=True)
        assert summary.cases_run == 0
        assert not (out / "case_001").exists()

    def test_missing_api_key_skips_model(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DEFINITELY_NOT_SET_KEY", raising=False)
        # A model that requires an unset env var, NOT in mock mode
        case = _case("case_001")
        model = ModelEntry(
            name="needs_real_key",
            provider="someprovider",
            api_key_env="DEFINITELY_NOT_SET_KEY",
        )
        out = tmp_path / "results"
        # mock=False, no mock responses → MissingAPIKeyError is caught and skipped
        summary = run_batch([case], [model], out_dir=out, mock=False)
        assert summary.skipped == 1
        assert ("case_001", "needs_real_key") in summary.failed_pairs
        assert not (out / "case_001").exists()
