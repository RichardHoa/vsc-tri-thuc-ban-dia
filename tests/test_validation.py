"""Validator: blockquote-aware diffing, bare-dash and footnote-chain structural checks."""

from __future__ import annotations

import json

from extractor.survey import FootnoteChain
from extractor.validation import (
    ExtractionValidator,
    check_footnote_chains,
    check_structure,
    normalize_for_diff,
    parse_markdown_story,
    split_rendered_segments,
    strip_markdown_scaffolding,
)

MD = """# I. NGUỒN GỐC SỰ VẬT

## 3. SỰ TÍCH CHIM HÍT CÔ

kêu lên:

> Cô hố cô hố.
> Bay về mà ăn![^2]

Có lẽ đây cũng là một dị bản.

---

### Chú thích

[^2]: (Trang 102) Theo Nguyễn Văn Ngọc.

[^4]: (Trang 240) Có câu ca dao:

    > Đôi ta như chim tử quy.

[^4]: (Trang 241)

    > Đêm nghe thấy tiếng.

    Hết.
"""


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_strip_scaffolding_removes_blockquote_marker_keeps_text():
    kept = strip_markdown_scaffolding(MD)
    assert "Cô hố cô hố." in kept.splitlines()
    assert "Bay về mà ăn!" in kept.splitlines()
    assert not any(line.lstrip().startswith(">") for line in kept.splitlines())
    assert "Đêm nghe thấy tiếng." in normalize_for_diff(kept)


def test_split_segments_blockquote_body_and_footnote_continuations():
    body, fns = split_rendered_segments(MD)
    assert body.splitlines() == [
        "kêu lên:",
        "Cô hố cô hố.",
        "Bay về mà ăn!",
        "Có lẽ đây cũng là một dị bản.",
    ]
    assert [(p, normalize_for_diff(t)) for p, t in fns] == [
        (102, "Theo Nguyễn Văn Ngọc."),
        (240, "Có câu ca dao: Đôi ta như chim tử quy."),
        (241, "Đêm nghe thấy tiếng. Hết."),
    ]


def test_parse_markdown_story_attaches_indented_lines_to_footnote(tmp_path):
    parsed = parse_markdown_story(_write(tmp_path, "s.md", MD))
    assert "Đôi ta" not in parsed["body"]
    assert "Cô hố cô hố." in parsed["body"].splitlines()
    assert parsed["footnotes"] == [(2, 102), (4, 240), (4, 241)]
    assert normalize_for_diff(parsed["footnote_entries"][2][2]) == "Đêm nghe thấy tiếng. Hết."


def _parsed(body, footnotes=()):
    return {
        "title": "T", "category": "C", "body": body,
        "footnotes": list(footnotes), "footnote_entries": [],
    }


def test_bare_dash_paragraph_is_flagged():
    flags, _ = check_structure(_parsed('Ngốc hỏi:\n-\n"Mua hả?".'), {})
    assert "BARE_DASH_PARAGRAPH" in flags


def test_dash_led_dialogue_is_not_flagged():
    flags, _ = check_structure(_parsed('Ngốc hỏi:\n- "Mua hả?".'), {})
    assert flags == []


def test_footnote_pages_out_of_story_range_flag_gap():
    flags, _ = check_structure(
        _parsed("a[^1].", [(1, 10), (1, 14)]), {"start_page": 10, "end_page": 12}
    )
    assert "FOOTNOTE_GAP:1" in flags


def test_footnote_pages_out_of_order_flag_gap():
    flags, _ = check_structure(
        _parsed("a[^1].", [(1, 11), (1, 10)]), {"start_page": 10, "end_page": 12}
    )
    assert "FOOTNOTE_GAP:1" in flags


def test_per_page_renumbering_with_skipped_pages_is_not_a_gap():
    # story 41: [^1] on 296, 299, 300, ... (pages 297-298 simply have no footnotes)
    flags, notes = check_structure(
        _parsed("a[^1].", [(1, 296), (1, 299), (1, 300)]), {"start_page": 296, "end_page": 311}
    )
    assert flags == []
    assert any("per-page renumbering" in n for n in notes)


def test_chain_complete():
    chains = [FootnoteChain(num=2, pages=[175, 176], snippet="")]
    assert check_footnote_chains([(2, 175), (2, 176)], chains, 170, 180) == []


def test_chain_with_lost_continuation_number_flags_gap():
    # pre-fix rendering: the page-176 continuation of [^2] came out as [^1]
    chains = [FootnoteChain(num=2, pages=[175, 176], snippet="")]
    assert check_footnote_chains([(2, 175), (1, 176)], chains, 170, 180) == ["FOOTNOTE_GAP:2"]


def test_chain_pages_outside_story_are_ignored():
    chains = [FootnoteChain(num=2, pages=[175, 176], snippet="")]
    assert check_footnote_chains([(2, 176)], chains, 176, 180) == []


def _toc(tmp_path, start, end):
    toc = {"sections": [{"stories": [{
        "story_number": 1, "title": "T", "start_page": start, "end_page": end,
        "markdown_file": "story_001.md", "footnote_count": None,
    }]}]}
    _write(tmp_path, "table_of_contents.json", json.dumps(toc, ensure_ascii=False))


def test_validate_section_flags_bare_dash_story_as_review(tmp_path, data_pdf):
    _toc(tmp_path, 307, 308)
    _write(tmp_path, "story_001.md", "# C\n\n## 1. T\n\nNgốc hỏi:\n\n-\n\n\"Mua hả?\".\n")
    results, _ = ExtractionValidator.validate_section(data_pdf.name, str(tmp_path))
    assert "BARE_DASH_PARAGRAPH" in results[0].structural_flags
    assert results[0].status == "REVIEW"


def test_validate_section_flags_lost_continuation(tmp_path, data_pdf):
    _toc(tmp_path, 175, 176)
    md = (
        "# C\n\n## 1. T\n\nx[^1] y[^2].\n\n---\n\n### Chú thích\n\n"
        "[^1]: (Trang 175) Theo Lăng-đờ (Landes). Sách đã dẫn.\n\n"
        "[^2]: (Trang 175) Xem thêm.\n\n"
        "[^1]: (Trang 176) Truyện bà mẹ Mục Liên đại khái như sau:\n"
    )
    _write(tmp_path, "story_001.md", md)
    results, _ = ExtractionValidator.validate_section(data_pdf.name, str(tmp_path))
    assert "FOOTNOTE_GAP:2" in results[0].structural_flags
