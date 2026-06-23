"""Tests for `lab.blind`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab.batch_runner import run_batch
from lab.blind import BlindModeError, generate_blind
from lab.case_loader import Case
from lab.model_registry import ModelEntry


def _case(cid: str = "case_001") -> Case:
    return Case(id=cid, category="understanding", tags=[], description="", body="hi")


def _model(name: str) -> ModelEntry:
    return ModelEntry(name=name, provider="mock", api_key_env="MOCK_KEY")


def _populate_results(results_dir: Path) -> None:
    """Run a quick mock batch so a results/<date>/case_001/{model}.md exists."""
    run_batch([_case()], [_model("a"), _model("b")], out_dir=results_dir, mock=True)


class TestGenerateBlind:
    def test_produces_three_files(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results"
        _populate_results(results_dir)
        blind_root = tmp_path / "blind"

        out = generate_blind(
            results_dir, "case_001", blind_root=blind_root, date="2026-06-23"
        )
        assert (out / "response_A.md").is_file()
        assert (out / "response_B.md").is_file()
        assert (out / "mapping.json").is_file()

    def test_mapping_round_trip(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results"
        _populate_results(results_dir)
        out = generate_blind(
            results_dir,
            "case_001",
            blind_root=tmp_path / "blind",
            date="2026-06-23",
        )
        mapping = json.loads((out / "mapping.json").read_text(encoding="utf-8"))
        assert mapping["case_id"] == "case_001"
        assert mapping["date"] == "2026-06-23"
        # Both A and B reference one of the two models
        assert mapping["A"] in {"a", "b"}
        assert mapping["B"] in {"a", "b"}
        assert mapping["A"] != mapping["B"]

    def test_seed_reproducible(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results"
        _populate_results(results_dir)
        out1 = generate_blind(
            results_dir,
            "case_001",
            blind_root=tmp_path / "blind1",
            date="2026-06-23",
            seed=42,
        )
        out2 = generate_blind(
            results_dir,
            "case_001",
            blind_root=tmp_path / "blind2",
            date="2026-06-23",
            seed=42,
        )
        m1 = json.loads((out1 / "mapping.json").read_text(encoding="utf-8"))
        m2 = json.loads((out2 / "mapping.json").read_text(encoding="utf-8"))
        assert m1 == m2

    def test_response_body_has_no_frontmatter(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results"
        _populate_results(results_dir)
        out = generate_blind(
            results_dir,
            "case_001",
            blind_root=tmp_path / "blind",
            date="2026-06-23",
            seed=1,
        )
        for label in ("A", "B"):
            text = (out / f"response_{label}.md").read_text(encoding="utf-8")
            assert not text.startswith("---"), (
                f"response_{label}.md leaked frontmatter: {text!r}"
            )

    def test_too_few_models_raises(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results"
        # Only one model
        run_batch([_case()], [_model("only")], out_dir=results_dir, mock=True)
        with pytest.raises(BlindModeError, match="at least 2"):
            generate_blind(
                results_dir,
                "case_001",
                blind_root=tmp_path / "blind",
                date="2026-06-23",
            )

    def test_missing_case_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(BlindModeError, match="Case directory not found"):
            generate_blind(
                tmp_path / "results",
                "absent",
                blind_root=tmp_path / "blind",
                date="2026-06-23",
            )

    def test_explicit_models_pair(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results"
        run_batch(
            [_case()],
            [_model("alpha"), _model("beta"), _model("gamma")],
            out_dir=results_dir,
            mock=True,
        )
        out = generate_blind(
            results_dir,
            "case_001",
            blind_root=tmp_path / "blind",
            date="2026-06-23",
            models=("alpha", "gamma"),
            seed=1,
        )
        mapping = json.loads((out / "mapping.json").read_text(encoding="utf-8"))
        assert {mapping["A"], mapping["B"]} == {"alpha", "gamma"}
