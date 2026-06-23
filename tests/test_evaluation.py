"""Tests for `lab.evaluation`."""

from __future__ import annotations

from pathlib import Path

import pytest

from lab.case_loader import Case
from lab.evaluation import generate_evaluation


def _case(cid: str = "case_001") -> Case:
    return Case(
        id=cid,
        category="understanding",
        tags=["emotion"],
        description="测潜台词",
        body="body text",
    )


class TestGenerateEvaluation:
    def test_writes_template_file(self, tmp_path: Path) -> None:
        blind_dir = tmp_path / "blind" / "case_001"
        blind_dir.mkdir(parents=True)
        out = generate_evaluation(
            _case(),
            blind_dir,
            out_dir=tmp_path / "evaluation",
            date="2026-06-23",
        )
        assert out.is_file()
        text = out.read_text(encoding="utf-8")
        assert "case_001" in text
        assert "测潜台词" in text

    def test_template_contains_winner_options(self, tmp_path: Path) -> None:
        blind_dir = tmp_path / "blind" / "case_001"
        blind_dir.mkdir(parents=True)
        text = generate_evaluation(
            _case(),
            blind_dir,
            out_dir=tmp_path / "evaluation",
            date="2026-06-23",
        ).read_text(encoding="utf-8")
        assert "- [ ] A" in text
        assert "- [ ] B" in text
        assert "- [ ] Tie" in text

    def test_template_contains_all_six_dimensions(self, tmp_path: Path) -> None:
        blind_dir = tmp_path / "blind" / "case_001"
        blind_dir.mkdir(parents=True)
        text = generate_evaluation(
            _case(),
            blind_dir,
            out_dir=tmp_path / "evaluation",
            date="2026-06-23",
        ).read_text(encoding="utf-8")
        for dim in (
            "Understanding",
            "Subtext Detection",
            "Humanity",
            "Beauty",
            "Curiosity",
            "Companionability",
        ):
            assert dim in text, f"Missing dimension {dim!r} in template."

    def test_subtext_dimension_listed_first(self, tmp_path: Path) -> None:
        """The background doc gives Subtext Detection the highest weight, so
        it should appear in the scoring table before the other dimensions."""
        blind_dir = tmp_path / "blind" / "case_001"
        blind_dir.mkdir(parents=True)
        text = generate_evaluation(
            _case(),
            blind_dir,
            out_dir=tmp_path / "evaluation",
            date="2026-06-23",
        ).read_text(encoding="utf-8")
        subtext_idx = text.find("Subtext Detection")
        understanding_idx = text.find("Understanding")
        assert -1 < understanding_idx < subtext_idx

    def test_missing_blind_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Blind packet not found"):
            generate_evaluation(
                _case(),
                tmp_path / "blind" / "absent",
                out_dir=tmp_path / "evaluation",
                date="2026-06-23",
            )
