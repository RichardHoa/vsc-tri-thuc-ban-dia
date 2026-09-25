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

[^4]: (Trang 240-241) Có câu ca dao:

    > Đôi ta như chim tử quy.
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
    assert [(p, e, normalize_for_diff(t)) for p, e, t in fns] == [
        (102, 102, "Theo Nguyễn Văn Ngọc."),
        (240, 241, "Có câu ca dao: Đôi ta như chim tử quy. Đêm nghe thấy tiếng. Hết."),
    ]


def test_parse_markdown_story_attaches_indented_lines_to_footnote(tmp_path):
    parsed = parse_markdown_story(_write(tmp_path, "s.md", MD))
    assert "Đôi ta" not in parsed["body"]
    assert "Cô hố cô hố." in parsed["body"].splitlines()
    assert parsed["footnotes"] == [(2, 102), (4, 240)]
    assert parsed["footnote_ranges"] == [(2, 102, 102), (4, 240, 241)]
    assert normalize_for_diff(parsed["footnote_entries"][1][2]) == (
        "Có câu ca dao: Đôi ta như chim tử quy. Đêm nghe thấy tiếng. Hết."
    )


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


def test_merged_chain_range_is_complete():
    chains = [FootnoteChain(num=2, pages=[175, 176], snippet="")]
    assert check_footnote_chains([(2, 175, 176)], chains, 170, 180) == []


def test_merged_range_out_of_story_flags_gap():
    flags, _ = check_structure(
        {**_parsed("a[^2].", [(2, 175)]), "footnote_ranges": [(2, 175, 177)]},
        {"start_page": 170, "end_page": 176},
    )
    assert "FOOTNOTE_GAP:2" in flags


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


# --- known source errata (textbook errors, allow-listed) --------------------

from extractor.validation import (  # noqa: E402
    KNOWN_SOURCE_ERRATA,
    StoryValidationResult,
    ValidationReporter,
    apply_source_errata,
)


def test_story_52_orphan_marker_3_is_a_known_erratum():
    assert (52, "ORPHAN_MARKER:3") in KNOWN_SOURCE_ERRATA


def test_apply_source_errata_moves_only_listed_flags():
    remaining, errata = apply_source_errata(52, ["ORPHAN_MARKER:3", "LOW_DENSITY"])
    assert remaining == ["LOW_DENSITY"]
    assert len(errata) == 1 and errata[0].startswith("ORPHAN_MARKER:3")
    # same flag on another story is still a real failure
    assert apply_source_errata(51, ["ORPHAN_MARKER:3"]) == (["ORPHAN_MARKER:3"], [])


def _result(**kw):
    base = dict(story_number=52, title="T", markdown_file="story_052.md", start_page=356,
                end_page=359, rendered_coverage=1.0, raw_coverage=1.0, char_per_page=2000.0)
    base.update(kw)
    return StoryValidationResult(**base)


def test_status_erratum_is_not_review():
    assert _result(source_errata=["ORPHAN_MARKER:3 — typo"]).status == "ERRATUM"
    assert _result(source_errata=["x"], structural_flags=["LOW_DENSITY"]).status == "REVIEW"
    assert _result(source_errata=["x"], rendered_coverage=0.5).status == "REVIEW"
    assert _result().status == "OK"


def test_report_lists_errata_separately():
    md = ValidationReporter.render_markdown([_result(source_errata=["ORPHAN_MARKER:3 — typo"])], [])
    assert "Needing review: **0**" in md
    assert "Known source errata: **1**" in md
    assert "## Known Source Errata" in md
    assert "ORPHAN_MARKER:3 — typo" in md
    assert "| ERRATUM |" in md


def test_validate_section_story_52_is_erratum(tmp_path, data_pdf):
    toc = {"sections": [{"stories": [{
        "story_number": 52, "title": "T", "start_page": 357, "end_page": 357,
        "markdown_file": "story_052.md", "footnote_count": None,
    }]}]}
    _write(tmp_path, "table_of_contents.json", json.dumps(toc))
    _write(tmp_path, "story_052.md", "# C\n\n## 52. T\n\nx[^3].\n")
    results, _ = ExtractionValidator.validate_section(data_pdf.name, str(tmp_path))
    assert "ORPHAN_MARKER:3" not in results[0].structural_flags
    assert results[0].source_errata and results[0].source_errata[0].startswith("ORPHAN_MARKER:3")


def test_validate_section_merged_continuation_is_clean(tmp_path, data_pdf):
    _toc(tmp_path, 175, 176)
    md = (
        "# C\n\n## 1. T\n\nx[^1] y[^2].\n\n---\n\n### Chú thích\n\n"
        "[^1]: (Trang 175) Theo Lăng-đờ (Landes). Sách đã dẫn.\n\n"
        "[^2]: (Trang 175-176) Xem thêm. Truyện bà mẹ Mục Liên đại khái như sau:\n"
    )
    _write(tmp_path, "story_001.md", md)
    results, _ = ExtractionValidator.validate_section(data_pdf.name, str(tmp_path))
    assert not [f for f in results[0].structural_flags if f.startswith("FOOTNOTE_GAP")]


def test_empty_footnote_is_flagged():
    parsed = {**_parsed("a[^1] b[^2].", [(1, 601), (2, 601)]),
              "footnote_entries": [(1, 601, ""), (2, 601, "Theo Phan Kế Bính.")]}
    flags, _ = check_structure(parsed, {})
    assert flags == ["EMPTY_FOOTNOTE:1"]


def test_story_97_empty_footnote_1_is_a_known_erratum():
    remaining, errata = apply_source_errata(97, ["EMPTY_FOOTNOTE:1"])
    assert remaining == [] and errata[0].startswith("EMPTY_FOOTNOTE:1")


def test_parse_markdown_story_keeps_empty_footnote_entry(tmp_path):
    md = "# C\n\n## 97. T\n\na[^1] b[^2].\n\n---\n\n### Chú thích\n\n[^1]: (Trang 601)\n\n[^2]: (Trang 601) Theo A.\n"
    parsed = parse_markdown_story(_write(tmp_path, "s.md", md))
    assert parsed["footnote_entries"] == [(1, 601, ""), (2, 601, "Theo A.")]


def test_story_108_orphan_marker_2_is_a_known_erratum():
    # page 657 prints both of its footnotes as "1." (body markers are 1 and 2)
    remaining, errata = apply_source_errata(108, ["ORPHAN_MARKER:2"])
    assert remaining == [] and errata[0].startswith("ORPHAN_MARKER:2")
