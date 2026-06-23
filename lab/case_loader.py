"""Case loader: parse YAML frontmatter + Markdown body from `cases/*.md` files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from lab.config import CATEGORIES


class CaseFormatError(ValueError):
    """Raised when a case file's frontmatter is missing or invalid."""


@dataclass
class Case:
    """A single test case loaded from disk."""

    id: str
    category: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    body: str = ""
    source_path: Path | None = None


# Frontmatter delimiters. The body MUST NOT begin with `---` (V1 constraint).
_FENCE = "---"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a `.md` file into (parsed YAML metadata dict, body string).

    Raises CaseFormatError if the file does not start with the `---` fence
    or if the closing fence is missing.
    """
    if not text.startswith(_FENCE):
        raise CaseFormatError(
            f"File does not start with {_FENCE!r} frontmatter fence. "
            "Add a YAML block delimited by --- at the top of the file."
        )

    # Skip the opening fence and the newline that follows it.
    after_open = text[len(_FENCE):]
    if not after_open.startswith("\n"):
        raise CaseFormatError("Opening fence must be followed by a newline.")
    after_open = after_open[1:]

    # Find the closing fence on its own line.
    close_idx = after_open.find("\n" + _FENCE)
    if close_idx == -1:
        raise CaseFormatError("Missing closing frontmatter fence (--- on its own line).")

    yaml_block = after_open[:close_idx]
    body = after_open[close_idx + 1 + len(_FENCE):]
    # Strip the newline at the end of the `---` line and one optional blank line.
    if body.startswith("\n\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]

    try:
        meta = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError as exc:
        raise CaseFormatError(f"Invalid YAML in frontmatter: {exc}") from exc

    if not isinstance(meta, dict):
        raise CaseFormatError("Frontmatter must be a YAML mapping (key: value pairs).")

    return meta, body


def _validate_metadata(meta: dict[str, Any], source: Path) -> None:
    """Ensure required fields are present and well-typed."""
    if "id" not in meta or not isinstance(meta["id"], str) or not meta["id"].strip():
        raise CaseFormatError(f"{source}: missing or empty `id` in frontmatter.")
    category = meta.get("category")
    if category not in CATEGORIES:
        raise CaseFormatError(
            f"{source}: `category`={category!r} is not in CATEGORIES. "
            f"Allowed: {sorted(CATEGORIES)}"
        )
    tags = meta.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise CaseFormatError(f"{source}: `tags` must be a list of strings.")
    description = meta.get("description", "")
    if not isinstance(description, str):
        raise CaseFormatError(f"{source}: `description` must be a string.")


def load_case(path: Path) -> Case:
    """Load a single case file. Raises CaseFormatError on invalid input."""
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    _validate_metadata(meta, path)
    return Case(
        id=meta["id"].strip(),
        category=meta["category"],
        tags=list(meta.get("tags", [])),
        description=meta.get("description", ""),
        body=body,
        source_path=path,
    )


def load_all_cases(cases_dir: Path) -> list[Case]:
    """Load every `cases/*.md` file, sorted by id for determinism.

    Directories are skipped. Files that fail to parse are surfaced as
    CaseFormatError so the caller (CLI) can decide whether to skip or abort.
    """
    if not cases_dir.is_dir():
        return []
    cases: list[Case] = []
    for path in sorted(cases_dir.glob("*.md")):
        cases.append(load_case(path))
    cases.sort(key=lambda c: c.id)
    return cases
