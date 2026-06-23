"""CLI smoke tests using Typer's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lab.cli import app


runner = CliRunner()


def _init_repo(root: Path) -> None:
    """Mirror the real repo layout inside a temp directory."""
    (root / "cases").mkdir()
    (root / "marathons").mkdir()
    (root / "models.yaml").write_text(
        "models:\n"
        "  - name: m1\n    provider: p\n    api_key_env: K1\n"
        "  - name: m2\n    provider: p\n    api_key_env: K2\n",
        encoding="utf-8",
    )
    case = (
        "---\nid: case_001\ncategory: understanding\n---\n\n我今天面试结束之后特别难受。\n"
    )
    (root / "cases" / "case_001.md").write_text(case, encoding="utf-8")

    scenario = root / "marathons" / "s"
    scenario.mkdir(parents=True)
    (scenario / "turn_01.md").write_text("hi", encoding="utf-8")
    (scenario / "turn_02.md").write_text("bye", encoding="utf-8")


@pytest.fixture
def isolated_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Run the CLI against a temp repo by monkey-patching the lab.cli root resolver."""
    _init_repo(tmp_path)

    import lab.cli as cli

    monkeypatch.setattr(cli, "_resolve_repo_root", lambda: tmp_path)
    return tmp_path


class TestCasesCommand:
    def test_cases_lists_loaded_cases(self, isolated_repo: Path) -> None:
        result = runner.invoke(app, ["cases"])
        assert result.exit_code == 0
        assert "case_001" in result.stdout


class TestModelsCommand:
    def test_models_shows_missing_keys(self, isolated_repo: Path) -> None:
        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "m1" in result.stdout
        assert "missing" in result.stdout.lower()


class TestRunCommand:
    def test_run_in_mock_mode_writes_files(self, isolated_repo: Path) -> None:
        result = runner.invoke(app, ["--mock"])
        assert result.exit_code == 0
        # One case × two models → 2 files
        day_dirs = list((isolated_repo / "results").iterdir())
        assert len(day_dirs) == 1
        case_dir = day_dirs[0] / "case_001"
        assert (case_dir / "m1.md").is_file()
        assert (case_dir / "m2.md").is_file()


class TestBlindCommand:
    def test_blind_creates_packet(self, isolated_repo: Path) -> None:
        # First run the batch in mock mode
        runner.invoke(app, ["--mock"])
        result = runner.invoke(app, ["blind", "case_001", "--seed", "1"])
        assert result.exit_code == 0
        blind_dir = isolated_repo / "blind" / "case_001"
        assert (blind_dir / "response_A.md").is_file()
        assert (blind_dir / "response_B.md").is_file()
        assert (blind_dir / "mapping.json").is_file()
        mapping = json.loads((blind_dir / "mapping.json").read_text(encoding="utf-8"))
        assert {mapping["A"], mapping["B"]} == {"m1", "m2"}


class TestEvalCommand:
    def test_eval_creates_template(self, isolated_repo: Path) -> None:
        runner.invoke(app, ["--mock"])
        runner.invoke(app, ["blind", "case_001", "--seed", "1"])
        result = runner.invoke(app, ["eval", "case_001"])
        assert result.exit_code == 0
        eval_files = list((isolated_repo / "evaluation").iterdir())
        assert len(eval_files) == 1
        text = eval_files[0].read_text(encoding="utf-8")
        assert "Subtext Detection" in text


class TestMarathonCommand:
    def test_marathon_writes_turn_files(self, isolated_repo: Path) -> None:
        result = runner.invoke(
            app, ["marathon", "s", "--model", "m1", "--mock"]
        )
        assert result.exit_code == 0
        day_dirs = list((isolated_repo / "results").iterdir())
        marathon_dir = day_dirs[0] / "marathon_s_m1"
        assert (marathon_dir / "turn_01.md").is_file()
        assert (marathon_dir / "turn_02.md").is_file()


class TestJournalCommand:
    def test_journal_new_creates_file(self, isolated_repo: Path) -> None:
        result = runner.invoke(app, ["journal", "new"])
        assert result.exit_code == 0
        journal_files = list((isolated_repo / "journal").iterdir())
        assert len(journal_files) == 1

    def test_journal_note_appends(self, isolated_repo: Path) -> None:
        result = runner.invoke(
            app, ["journal", "note", "Response B 让我停下来想了一会。"]
        )
        assert result.exit_code == 0
        journal_files = list((isolated_repo / "journal").iterdir())
        assert len(journal_files) == 1
        text = journal_files[0].read_text(encoding="utf-8")
        assert "Response B 让我停下来想了一会。" in text


class TestDefaultBehavior:
    def test_no_args_runs_batch(self, isolated_repo: Path) -> None:
        result = runner.invoke(app, ["--mock"])
        assert result.exit_code == 0
        # If it ran the batch, results/ was populated
        assert (isolated_repo / "results").is_dir()
