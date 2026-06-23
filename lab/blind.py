"""Blind comparison mode: take two model outputs, randomly assign to A/B.

Output layout (PRD §Feature 4):
    blind/
      <case_id>/
        response_A.md
        response_B.md
        mapping.json   # {"A": "minimax3", "B": "deepseek_v4", ...}
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


class BlindModeError(RuntimeError):
    """Raised when blind mode cannot produce a packet."""


@dataclass
class BlindMapping:
    A: str
    B: str
    case_id: str
    date: str

    def to_dict(self) -> dict[str, str]:
        return {"A": self.A, "B": self.B, "case_id": self.case_id, "date": self.date}


def _list_model_outputs(case_dir: Path) -> list[tuple[str, Path]]:
    """Return (model_name, response_path) for every model file in a case dir."""
    if not case_dir.is_dir():
        raise BlindModeError(f"Case directory not found: {case_dir}")
    outputs: list[tuple[str, Path]] = []
    for path in sorted(case_dir.glob("*.md")):
        outputs.append((path.stem, path))
    if len(outputs) < 2:
        raise BlindModeError(
            f"Need at least 2 model outputs in {case_dir}, found {len(outputs)}."
        )
    return outputs


def _extract_response_body(md_path: Path) -> str:
    """Return the body of a model output file (everything after the closing frontmatter fence)."""
    text = md_path.read_text(encoding="utf-8")
    # Find the second --- that closes the frontmatter.
    # The file MUST start with `---` per batch_runner output format.
    if not text.startswith("---"):
        return text  # not frontmatter; return as-is
    after_open = text[3:]
    if not after_open.startswith("\n"):
        return text
    after_open = after_open[1:]
    close_idx = after_open.find("\n---")
    if close_idx == -1:
        return text
    body = after_open[close_idx + 4:]
    if body.startswith("\n"):
        body = body[1:]
    return body


def generate_blind(
    results_root: Path,
    case_id: str,
    *,
    blind_root: Path,
    date: str,
    models: tuple[str, str] | None = None,
    seed: int | None = None,
) -> Path:
    """Generate a blind comparison packet for one case.

    Args:
        results_root: `results/YYYY-MM-DD/` directory.
        case_id: The case to blind-compare (e.g. "case_001").
        blind_root: The `blind/` directory (output root).
        date: Date string for the mapping (typically YYYY-MM-DD).
        models: Optional explicit pair of model names. If None, picks the first
            two model files in sorted order from the case directory.
        seed: Optional seed for the A/B assignment (reproducible).

    Returns:
        The path to the generated blind directory.

    Raises:
        BlindModeError: If there aren't enough model outputs.
    """
    case_dir = results_root / case_id
    available = _list_model_outputs(case_dir)

    if models is not None:
        by_name = {name: path for name, path in available}
        missing = [m for m in models if m not in by_name]
        if missing:
            raise BlindModeError(
                f"Model(s) {missing} not found in {case_dir}. "
                f"Available: {list(by_name)}"
            )
        chosen = [(m, by_name[m]) for m in models]
    else:
        chosen = available[:2]

    rng = random.Random(seed)
    pair = list(chosen)
    rng.shuffle(pair)
    mapping = BlindMapping(A=pair[0][0], B=pair[1][0], case_id=case_id, date=date)

    out_dir = blind_root / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "response_A.md").write_text(
        _extract_response_body(pair[0][1]), encoding="utf-8"
    )
    (out_dir / "response_B.md").write_text(
        _extract_response_body(pair[1][1]), encoding="utf-8"
    )
    (out_dir / "mapping.json").write_text(
        json.dumps(mapping.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_dir
