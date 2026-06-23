"""Tests for `lab.marathon_runner` (B 组: continuous session)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from lab.marathon_runner import MarathonSummary, _load_turns, run_marathon
from lab.model_registry import ModelEntry


def _model(name: str = "minimax3") -> ModelEntry:
    return ModelEntry(name=name, provider="mock", api_key_env="MOCK_KEY")


class TestLoadTurns:
    def test_loads_in_lexicographic_order(self, tmp_path: Path) -> None:
        scenario = tmp_path / "test_scenario"
        scenario.mkdir()
        (scenario / "turn_02.md").write_text("second", encoding="utf-8")
        (scenario / "turn_01.md").write_text("first", encoding="utf-8")
        (scenario / "turn_03.md").write_text("third", encoding="utf-8")
        # Add a non-matching file to confirm it's ignored
        (scenario / "notes.md").write_text("ignored", encoding="utf-8")

        assert _load_turns(tmp_path, "test_scenario") == ["first", "second", "third"]

    def test_missing_scenario_lists_available(self, tmp_path: Path) -> None:
        (tmp_path / "other_scenario").mkdir()
        with pytest.raises(FileNotFoundError, match="Available scenarios"):
            _load_turns(tmp_path, "absent")

    def test_empty_scenario_dir_raises(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()
        with pytest.raises(FileNotFoundError, match="at least one turn"):
            _load_turns(tmp_path, "empty")


class TestRunMarathonSignature:
    """Design guard: no reset/clear/new_session function in this module."""

    def test_no_reset_or_clear_functions(self) -> None:
        import lab.marathon_runner as mod

        forbidden_prefixes = ("reset_", "clear_", "new_session_", "restart_")
        offenders = [
            name
            for name in dir(mod)
            if name.startswith(forbidden_prefixes) and callable(getattr(mod, name))
        ]
        assert not offenders, (
            f"marathon_runner exposes session-resetting functions {offenders}. "
            "B 组 requires that the conversation context is never reset."
        )

    def test_run_marathon_signature(self) -> None:
        sig = inspect.signature(run_marathon)
        # Must NOT have a way to inject messages from outside.
        assert "messages" not in sig.parameters


class TestRunMarathon:
    def test_writes_per_turn_snapshots(self, tmp_path: Path) -> None:
        marathons = tmp_path / "marathons"
        scenario = marathons / "career"
        scenario.mkdir(parents=True)
        for i, text in enumerate(
            ["我今天和领导吵架了。", "其实也不算吵架。", "主要是他笑了一下。"],
            start=1,
        ):
            (scenario / f"turn_{i:02d}.md").write_text(text, encoding="utf-8")

        out = tmp_path / "results"
        summary = run_marathon(
            "career",
            _model(),
            marathons_dir=marathons,
            out_dir=out,
            mock=True,
        )
        assert isinstance(summary, MarathonSummary)
        assert summary.turns_run == 3
        assert summary.scenario == "career"
        marathon_dir = out / "marathon_career_minimax3"
        assert marathon_dir.is_dir()
        assert (marathon_dir / "turn_01.md").is_file()
        assert (marathon_dir / "turn_02.md").is_file()
        assert (marathon_dir / "turn_03.md").is_file()

    def test_each_turn_contains_full_history(self, tmp_path: Path) -> None:
        marathons = tmp_path / "marathons"
        scenario = marathons / "s"
        scenario.mkdir(parents=True)
        (scenario / "turn_01.md").write_text("第一轮用户输入", encoding="utf-8")
        (scenario / "turn_02.md").write_text("第二轮用户输入", encoding="utf-8")

        out = tmp_path / "results"
        run_marathon("s", _model(), marathons_dir=marathons, out_dir=out, mock=True)

        turn1 = (out / "marathon_s_minimax3" / "turn_01.md").read_text(encoding="utf-8")
        turn2 = (out / "marathon_s_minimax3" / "turn_02.md").read_text(encoding="utf-8")

        # Turn 1 snapshot: only one user message + one assistant reply
        assert "第一轮用户输入" in turn1
        assert "第二轮用户输入" not in turn1
        assert turn1.count("## User") == 1
        assert turn1.count("## Assistant") == 1

        # Turn 2 snapshot: BOTH user messages + BOTH assistant replies are visible
        assert "第一轮用户输入" in turn2
        assert "第二轮用户输入" in turn2
        assert turn2.count("## User") == 2
        assert turn2.count("## Assistant") == 2

    def test_mock_responses_appear_in_transcript(self, tmp_path: Path) -> None:
        marathons = tmp_path / "marathons"
        scenario = marathons / "s"
        scenario.mkdir(parents=True)
        (scenario / "turn_01.md").write_text("hi", encoding="utf-8")

        out = tmp_path / "results"
        run_marathon(
            "s",
            _model(),
            marathons_dir=marathons,
            out_dir=out,
            mock=True,
            mock_responses={"minimax3": "MOCK-CUSTOM-RESPONSE"},
        )
        text = (out / "marathon_s_minimax3" / "turn_01.md").read_text(encoding="utf-8")
        assert "MOCK-CUSTOM-RESPONSE" in text

    def test_missing_scenario_raises(self, tmp_path: Path) -> None:
        marathons = tmp_path / "marathons"
        marathons.mkdir()
        out = tmp_path / "results"
        with pytest.raises(FileNotFoundError, match="Available scenarios"):
            run_marathon(
                "ghost",
                _model(),
                marathons_dir=marathons,
                out_dir=out,
                mock=True,
            )
