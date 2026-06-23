"""Project-wide constants: paths, category enum, evaluation dimensions, weights."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    """All paths are resolved relative to the repository root."""

    root: Path
    cases: Path
    models_yaml: Path
    results: Path
    blind: Path
    evaluation: Path
    journal: Path
    marathons: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        return cls(
            root=root,
            cases=root / "cases",
            models_yaml=root / "models.yaml",
            results=root / "results",
            blind=root / "blind",
            evaluation=root / "evaluation",
            journal=root / "journal",
            marathons=root / "marathons",
        )


# 8 fixed categories (PRD §Case Format). Adding a new category is a deliberate act.
CATEGORIES: frozenset[str] = frozenset(
    {
        "understanding",
        "decision",
        "emotion",
        "companionship",
        "writing",
        "creativity",
        "reflection",
        "long_conversation",
    }
)

# 6 evaluation dimensions (PRD §Evaluation Framework).
# Subtext Detection is listed first because the background doc gives it 30% weight.
DIMENSIONS: tuple[str, ...] = (
    "Understanding",
    "Subtext Detection",
    "Humanity",
    "Beauty",
    "Curiosity",
    "Companionability",
)

# Per background document: subtext understanding is the single most important
# differentiator. Any future "weight" calculation must keep this ≥25%.
SUBTEXT_WEIGHT = 0.30

DEFAULT_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_TEMPERATURE = 0.7
