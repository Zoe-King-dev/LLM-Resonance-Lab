"""Resonance journal: free-form subjective feelings about a model response.

The journal is intentionally unstructured — quantification is discouraged.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _today(date: str | None = None) -> str:
    if date is not None:
        return date
    return datetime.now().strftime("%Y-%m-%d")


def create_journal_entry(
    *,
    journal_root: Path,
    date: str | None = None,
) -> Path:
    """Create an empty journal entry for the given date.

    If the file already exists, this is a no-op (the user can append to it).

    Returns the path to the journal file.
    """
    journal_root.mkdir(parents=True, exist_ok=True)
    day = _today(date)
    path = journal_root / f"{day}.md"
    if not path.exists():
        header = (
            f"# Resonance Journal — {day}\n\n"
            "记录你今天最真实的模型体验。允许模糊感受，不强制量化。\n\n"
            "---\n\n"
        )
        path.write_text(header, encoding="utf-8")
    return path


def append_journal_note(
    text: str,
    *,
    journal_root: Path,
    date: str | None = None,
) -> Path:
    """Append a dated note to the journal entry for the given day.

    The note is prefixed with a timestamp so the order of notes is preserved.
    """
    path = create_journal_entry(journal_root=journal_root, date=date)
    timestamp = datetime.now().strftime("%H:%M")
    day = _today(date)
    body = f"\n## {timestamp} ({day})\n\n{text.rstrip()}\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(body)
    return path
