"""
MỤC LỤC → Part → Section resolution and the shared ``--part`` / ``--section``
selection rules (against the real data.pdf).
"""

from __future__ import annotations

import pytest

from extractor.toc import TableOfContentsParser


@pytest.fixture(scope="module")
def parts(data_pdf):
    return TableOfContentsParser.parse_parts(data_pdf)


def _ranges(part):
    return [(s.roman, s.start_page, s.end_page) for s in part.sections]


def test_three_parts_with_page_ranges_from_muc_luc(parts):
    # Part 2's heading repeats once per Volume; only its first occurrence opens it.
    # Part 3 ends where LỜI SAU SÁCH begins (p. 1434).
    assert [(p.number, p.start_page, p.end_page) for p in parts] == [
        (1, 42, 84), (2, 85, 1338), (3, 1339, 1433),
    ]
    assert [p.folder_name for p in parts] == ["PHAN_THU_NHAT", "PHAN_THU_HAI", "PHAN_THU_BA"]
    assert parts[0].title == "NGHIÊN CỨU TRUYỆN CỔ TÍCH NÓI CHUNG VÀ TRUYỆN CỔ TÍCH VIỆT-NAM"
    assert parts[2].title == "NHẬN ĐỊNH TỔNG QUÁT VỀ KHO TÀNG TRUYỆN CỔ TÍCH VIỆT-NAM"
    assert [p.leaf_kind for p in parts] == ["essays", "stories", "essays"]


def test_part_1_sections(parts):
    assert _ranges(parts[0]) == [("I", 43, 58), ("II", 59, 72), ("III", 73, 84)]


def test_part_3_sections_continue_part_1_numbering(parts):
    # "3.TÍNH CÁCH ..." (no space after the dot) is still an Essay entry, not
    # non-Essay material that would close Section IV early.
    assert _ranges(parts[2]) == [("IV", 1341, 1391), ("V", 1392, 1433)]
    assert [s.index for s in parts[2].sections] == [1, 2]


def test_part_2_sections_unchanged(parts):
    sections = parts[1].sections
    assert [s.roman for s in sections] == ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    assert (sections[0].start_page, sections[0].end_page) == (86, 203)
    assert (sections[8].start_page, sections[8].end_page) == (1123, 1255)
    assert (sections[9].start_page, sections[9].end_page) == (1256, 1338)
    # Volume front matter inside Section III stays a hard stop.
    assert 284 in sections[2].hard_stops


def test_section_folder_names_do_not_collide_across_parts(parts):
    part2_iv = parts[1].sections[3]
    part3_iv = parts[2].sections[0]
    assert part2_iv.roman == part3_iv.roman == "IV"
    assert part2_iv.path != part3_iv.path
    assert part3_iv.path == "PHAN_THU_BA/IV_DAC_DIEM_CUA_TRUYEN_CO_TICH_VIET_NAM"


# --- selection rules -------------------------------------------------------


def test_no_selection_means_all_three_parts(parts):
    selected = TableOfContentsParser.select_parts(parts, None, None)
    assert [(p.number, len(secs)) for p, secs in selected] == [(1, 3), (2, 10), (3, 2)]


def test_part_without_section_selects_whole_part(parts):
    selected = TableOfContentsParser.select_parts(parts, 1, None)
    assert [(p.number, [s.roman for s in secs]) for p, secs in selected] == [(1, ["I", "II", "III"])]


def test_part_3_section_2_is_section_v(parts):
    [(part, sections)] = TableOfContentsParser.select_parts(parts, 3, "2")
    assert part.number == 3
    assert [s.roman for s in sections] == ["V"]


def test_section_without_part_is_an_error(parts):
    with pytest.raises(ValueError, match="--section requires --part"):
        TableOfContentsParser.select_parts(parts, None, "2")


def test_unknown_part_is_an_error(parts):
    with pytest.raises(ValueError, match="--part"):
        TableOfContentsParser.select_parts(parts, 4, None)
