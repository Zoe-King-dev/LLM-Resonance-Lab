"""Human evaluation workspace: generate the evaluation template for a case.

This module NEVER calls an LLM to score another LLM's response. That would
violate the "Human Judgment Matters" principle (PRD §Design Principles).
"""

from __future__ import annotations

from pathlib import Path

from lab.config import DIMENSIONS
from lab.case_loader import Case


def _render_template(case: Case, date: str) -> str:
    """Render the PRD §Feature 5 evaluation template for a case."""
    lines: list[str] = []
    lines.append(f"# Evaluation — {case.id}")
    lines.append("")
    lines.append(f"- Case: `{case.id}`")
    lines.append(f"- Category: `{case.category}`")
    lines.append(f"- Date: {date}")
    lines.append(f"- Description: {case.description or '_(no description)_'}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Winner")
    lines.append("")
    lines.append("- [ ] A")
    lines.append("- [ ] B")
    lines.append("- [ ] Tie")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Dimension Scores")
    lines.append("")
    lines.append("Fill in 0–10 for each dimension. **Do not look at the mapping.json yet.**")
    lines.append("")
    lines.append("| Dimension | A | B |")
    lines.append("| --- | --- | --- |")
    for dim in DIMENSIONS:
        lines.append(f"| {dim} |  |  |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("A:")
    lines.append("")
    lines.append("> ")
    lines.append("")
    lines.append("B:")
    lines.append("")
    lines.append("> ")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Reflection (after revealing the mapping)")
    lines.append("")
    lines.append("- Which response felt more **human**?")
    lines.append("- Which one caught the **subtext**?")
    lines.append("- Which one would you want as a long-term Agent core?")
    lines.append("")
    return "\n".join(lines)


def generate_evaluation(
    case: Case,
    blind_dir: Path,
    *,
    out_dir: Path,
    date: str,
) -> Path:
    """Write the evaluation template for one case.

    Args:
        case: The case being evaluated.
        blind_dir: The blind packet directory (just for existence check).
        out_dir: Where to write the evaluation file. Normally `evaluation/`.
        date: Date string for the filename and template header.

    Returns:
        The path to the generated evaluation file.

    Raises:
        FileNotFoundError: If `blind_dir` does not exist.
    """
    if not blind_dir.is_dir():
        raise FileNotFoundError(
            f"Blind packet not found: {blind_dir}. "
            "Run `python run.py blind <case_id>` first."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date}_{case.id}_evaluation.md"
    out_path.write_text(_render_template(case, date), encoding="utf-8")
    return out_path
