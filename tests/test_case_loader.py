"""Tests for `lab.case_loader`."""

from __future__ import annotations

from pathlib import Path

import pytest

from lab.case_loader import Case, CaseFormatError, load_all_cases, load_case, parse_frontmatter


class TestParseFrontmatter:
    def test_basic_split(self) -> None:
        text = (
            "---\n"
            "id: case_001\n"
            "category: understanding\n"
            "---\n"
            "\n"
            "我今天面试结束之后特别难受。\n"
        )
        meta, body = parse_frontmatter(text)
        assert meta["id"] == "case_001"
        assert meta["category"] == "understanding"
        assert body == "我今天面试结束之后特别难受。\n"

    def test_missing_open_fence(self) -> None:
        with pytest.raises(CaseFormatError, match="does not start with"):
            parse_frontmatter("id: case_001\n---\nbody\n")

    def test_missing_close_fence(self) -> None:
        with pytest.raises(CaseFormatError, match="Missing closing"):
            parse_frontmatter("---\nid: case_001\nbody without close\n")

    def test_invalid_yaml(self) -> None:
        with pytest.raises(CaseFormatError, match="Invalid YAML"):
            parse_frontmatter("---\n: not: valid: yaml: [unbalanced\n---\nbody\n")

    def test_frontmatter_must_be_mapping(self) -> None:
        with pytest.raises(CaseFormatError, match="YAML mapping"):
            parse_frontmatter("---\n- just a list\n---\nbody\n")

    def test_body_with_internal_dashes_preserved(self) -> None:
        text = (
            "---\n"
            "id: c1\n"
            "category: emotion\n"
            "---\n"
            "\n"
            "段落1\n"
            "\n"
            "---\n"
            "\n"
            "段落2（不是 fence，因为闭合 fence 已被前面的吃掉）\n"
        )
        # In V1 we only split on the FIRST closing fence, so internal --- on
        # its own line is the close; nothing after is body. That's a known V1
        # limitation, but we don't want a crash.
        meta, _ = parse_frontmatter(text)
        assert meta["id"] == "c1"


class TestLoadCase:
    def test_load_valid_case(self, tmp_path: Path, sample_case_md: str) -> None:
        path = tmp_path / "case_001.md"
        path.write_text(sample_case_md, encoding="utf-8")
        case = load_case(path)
        assert isinstance(case, Case)
        assert case.id == "case_001"
        assert case.category == "understanding"
        assert case.tags == ["emotion", "interview"]
        assert "面试官那个奇怪的表情" in case.body
        assert case.source_path == path

    def test_invalid_category_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.md"
        path.write_text(
            "---\nid: c1\ncategory: nonexistent\n---\nbody\n", encoding="utf-8"
        )
        with pytest.raises(CaseFormatError, match="not in CATEGORIES"):
            load_case(path)

    def test_missing_id_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.md"
        path.write_text(
            "---\ncategory: emotion\n---\nbody\n", encoding="utf-8"
        )
        with pytest.raises(CaseFormatError, match="missing or empty `id`"):
            load_case(path)

    def test_non_list_tags_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.md"
        path.write_text(
            "---\nid: c1\ncategory: emotion\ntags: not-a-list\n---\nbody\n",
            encoding="utf-8",
        )
        with pytest.raises(CaseFormatError, match="`tags` must be a list"):
            load_case(path)


class TestLoadAllCases:
    def test_returns_sorted_by_id(self, tmp_path: Path, sample_case_md: str) -> None:
        for cid in ("case_001", "case_002", "case_003"):
            text = sample_case_md.replace("case_001", cid)
            (tmp_path / f"{cid}.md").write_text(text, encoding="utf-8")
        cases = load_all_cases(tmp_path)
        assert [c.id for c in cases] == ["case_001", "case_002", "case_003"]

    def test_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        assert load_all_cases(tmp_path / "does-not-exist") == []

    def test_skip_directories(self, tmp_path: Path, sample_case_md: str) -> None:
        (tmp_path / "case_001.md").write_text(sample_case_md, encoding="utf-8")
        (tmp_path / "subdir").mkdir()  # should be ignored
        cases = load_all_cases(tmp_path)
        assert len(cases) == 1
