"""Markdown rendering of verse blocks (body + footnotes)."""

from __future__ import annotations

from extractor.formatters import MarkdownRenderer
from extractor.models import Footnote, StoryContent, Verse


def _story(**kw):
    base = dict(category="I. C", story_number=1, title="T", start_page=1, end_page=2)
    base.update(kw)
    return StoryContent(**base)


def test_verse_renders_as_blockquote_in_place():
    md = MarkdownRenderer.render(_story(paragraphs=[
        "kêu lên:",
        Verse(["Cô hố cô hố.", "Lúa đã trổ,", "Đỗ đã chín,", "Bay về mà ăn![^2]"]),
        "Có lẽ đây cũng là một dị bản.",
    ]))
    assert (
        "kêu lên:\n\n"
        "> Cô hố cô hố.\n> Lúa đã trổ,\n> Đỗ đã chín,\n> Bay về mà ăn![^2]\n\n"
        "Có lẽ đây cũng là một dị bản.\n"
    ) in md


def test_verse_in_khao_di_renders_as_blockquote():
    md = MarkdownRenderer.render(_story(paragraphs=["x."], khao_di=[Verse(["a,", "b."])]))
    assert "### KHẢO DỊ\n\n> a,\n> b.\n" in md


def test_plain_footnote_rendering_unchanged():
    md = MarkdownRenderer.render(_story(
        paragraphs=["x[^1]."],
        footnotes=[Footnote(id=1, orig_num=1, page=5, text="Theo A.")],
    ))
    assert md.endswith("[^1]: (Trang 5) Theo A.\n")


def test_footnote_with_verse_part_renders_indented_blockquote():
    fn = Footnote(
        id=4, orig_num=4, page=240, text="Có câu ca dao: Đôi ta như chim tử quy.",
        parts=["Có câu ca dao:", Verse(["Đôi ta như chim tử quy."])],
    )
    md = MarkdownRenderer.render(_story(paragraphs=["x[^4]."], footnotes=[fn]))
    assert md.endswith(
        "[^4]: (Trang 240) Có câu ca dao:\n\n"
        "    > Đôi ta như chim tử quy.\n"
    )


def test_footnote_starting_with_verse_then_prose():
    fn = Footnote(
        id=4, orig_num=4, page=241, text="Đêm nghe. Rồi.",
        parts=[Verse(["Đêm nghe."]), "Rồi."], continued=True,
    )
    md = MarkdownRenderer.render(_story(paragraphs=["x[^4]."], footnotes=[fn]))
    assert md.endswith(
        "[^4]: (Trang 241)\n\n"
        "    > Đêm nghe.\n\n"
        "    Rồi.\n"
    )


def test_merged_footnote_shows_page_range():
    fn = Footnote(id=2, orig_num=2, page=175, end_page=176, text="Xem thêm. Truyện bà mẹ.")
    md = MarkdownRenderer.render(_story(paragraphs=["x[^2]."], footnotes=[fn]))
    assert md.endswith("[^2]: (Trang 175-176) Xem thêm. Truyện bà mẹ.\n")
