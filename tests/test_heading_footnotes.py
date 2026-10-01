"""Heading footnotes: a marker printed in a Story or Section heading renders at
its printed position; manifest titles stay clean."""

from __future__ import annotations

import pytest

from extractor.discovery import StoryDiscoveryEngine, insert_heading_markers
from extractor.formatters import MarkdownRenderer
from extractor.models import StoryContent


# --- marker placement -------------------------------------------------------


def test_trailing_marker():
    assert insert_heading_markers("SỰ TÍCH CÁ HE", "13. SỰ TÍCH CÁ HE[^1]") == "SỰ TÍCH CÁ HE[^1]"


def test_mid_title_marker_keeps_printed_position():
    assert insert_heading_markers(
        "GỐC TÍCH RUỘNG THÁC ĐAO HAY LÀ TRUYỆN LÊ PHỤNG HIỂU",
        "25. GỐC TÍCH RUỘNG THÁC ĐAO[^1] HAY LÀ TRUYỆN LÊ PHỤNG HIỂU",
    ) == "GỐC TÍCH RUỘNG THÁC ĐAO[^1] HAY LÀ TRUYỆN LÊ PHỤNG HIỂU"


def test_marker_set_apart_by_a_space_attaches_to_the_word():
    assert insert_heading_markers("A B", "1. A B [^1]") == "A B[^1]"


def test_several_markers_keep_their_positions():
    assert insert_heading_markers("KIỆN NGÀNH ĐA", "57. KIỆN[^1] NGÀNH[^2] ĐA") == "KIỆN[^1] NGÀNH[^2] ĐA"
    assert insert_heading_markers("ABC", "1. ABC[^1][^2]") == "ABC[^1][^2]"


def test_no_marker_returns_title():
    assert insert_heading_markers("A B", "1. A B") == "A B"


def test_text_mismatch_falls_back_to_clean_title():
    # The marked text must end with the same letters as the clean title.
    assert insert_heading_markers("A B", "1. A[^1] C") == "A B"


# --- real headings in data.pdf ----------------------------------------------


@pytest.fixture(scope="module")
def stories(data_pdf):
    found = StoryDiscoveryEngine.discover_stories(data_pdf, 86, 203)
    found += StoryDiscoveryEngine.discover_stories(data_pdf, 255, 414)
    return {s.story_number: s for s in found}


@pytest.mark.parametrize("number,heading", [
    (13, "SỰ TÍCH CÁ HE[^1]"),
    (21, "SỰ TÍCH ÔNG ĐẦU RAU[^1]"),
    (25, "GỐC TÍCH RUỘNG THÁC ĐAO[^1] HAY LÀ TRUYỆN LÊ PHỤNG HIỂU"),
    (47, "CON VỢ KHÔN LẤY THẰNG CHỒNG DẠI NHƯ BÔNG HOA LÀI[^1] CẮM BÃI CỨT TRÂU"),
    (55, "VẬN KHỨ HOÀI SƠN NĂNG TRÍ TỬ, THỜI LAI BẠCH THỦY KHẢ THÔI SINH[^1]"),
    (57, "KIỆN NGÀNH[^1] ĐA"),
])
def test_real_story_heading_marker(stories, number, heading):
    story = stories[number]
    assert story.heading_title == heading
    assert "[^" not in story.title
    assert story.title == heading.replace("[^1]", "")


@pytest.mark.parametrize("number", [36, 41])
def test_real_section_heading_marker_goes_to_the_story_on_its_page(stories, number):
    # Section III's heading (p. 255, and its repeat opening Tập II on p. 296).
    assert stories[number].category_heading == "III. SỰ TÍCH CÁC CÂU VÍ[^1]"
    assert stories[number].category == "III. SỰ TÍCH CÁC CÂU VÍ"


def test_real_unmarked_headings_have_no_marked_variant(stories):
    assert stories[37].heading_title is None
    assert stories[37].category_heading is None


# --- rendering --------------------------------------------------------------


def test_render_uses_marked_headings():
    md = MarkdownRenderer.render(StoryContent(
        category="III. C", story_number=57, title="KIỆN NGÀNH ĐA", start_page=1, end_page=1,
        heading_title="KIỆN NGÀNH[^1] ĐA", category_heading="III. C[^2]", paragraphs=["x."],
    ))
    assert md.startswith("# III. C[^2]\n\n## 57. KIỆN NGÀNH[^1] ĐA\n")
