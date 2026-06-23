"""Tests for `lab.journal`."""

from __future__ import annotations

from pathlib import Path

from lab.journal import append_journal_note, create_journal_entry


class TestCreateJournalEntry:
    def test_creates_file(self, tmp_path: Path) -> None:
        path = create_journal_entry(journal_root=tmp_path, date="2026-06-23")
        assert path == tmp_path / "2026-06-23.md"
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "2026-06-23" in text
        assert "Resonance Journal" in text

    def test_idempotent(self, tmp_path: Path) -> None:
        path1 = create_journal_entry(journal_root=tmp_path, date="2026-06-23")
        first_text = path1.read_text(encoding="utf-8")
        path2 = create_journal_entry(journal_root=tmp_path, date="2026-06-23")
        assert path1 == path2
        # Content should be unchanged on second call
        assert path2.read_text(encoding="utf-8") == first_text

    def test_explicit_date_used(self, tmp_path: Path) -> None:
        path = create_journal_entry(journal_root=tmp_path, date="2025-01-15")
        assert path.name == "2025-01-15.md"


class TestAppendJournalNote:
    def test_appends_under_dated_header(self, tmp_path: Path) -> None:
        path = append_journal_note(
            "Response B 让我停下来想了一会。",
            journal_root=tmp_path,
            date="2026-06-23",
        )
        text = path.read_text(encoding="utf-8")
        assert "Response B 让我停下来想了一会。" in text
        assert "2026-06-23" in text

    def test_multiple_notes_accumulate(self, tmp_path: Path) -> None:
        append_journal_note(
            "first note", journal_root=tmp_path, date="2026-06-23"
        )
        append_journal_note(
            "second note", journal_root=tmp_path, date="2026-06-23"
        )
        text = (tmp_path / "2026-06-23.md").read_text(encoding="utf-8")
        assert "first note" in text
        assert "second note" in text

    def test_different_dates_separate_files(self, tmp_path: Path) -> None:
        append_journal_note("day1", journal_root=tmp_path, date="2026-06-23")
        append_journal_note("day2", journal_root=tmp_path, date="2026-06-24")
        assert (tmp_path / "2026-06-23.md").is_file()
        assert (tmp_path / "2026-06-24.md").is_file()
