"""Story extraction: dialogue carried across page breaks, verse kept as Verse blocks."""

from __future__ import annotations

import pytest
from conftest import FOOTNOTE_SIZE, Item, SyntheticPage

from extractor.discovery import StoryDiscoveryEngine
from extractor.engine import StoryExtractionEngine
from extractor.models import ExtractorConfig, StoryDefinition, Verse


def _extract(doc, start=1, end=None):
    end = end if end is not None else len(doc)
    story = StoryDefinition(
        story_number=1, title="T", category="C", start_page=start, end_page=end, start_y0=0.0
    )
    return StoryExtractionEngine.extract_single_story(doc, story, ExtractorConfig())


# --- dialogue across a page boundary ---------------------------------------


def test_bare_dash_at_page_end_joins_next_page(make_pdf):
    doc = make_pdf([
        SyntheticPage([
            Item(99, 100, "Narrative line one."),
            Item(99, 130, "He asked: -"),
        ]),
        SyntheticPage([Item(88, 100, '"Buy it?". The leaves moved.')]),
    ])
    assert _extract(doc).paragraphs == [
        "Narrative line one.",
        "He asked:",
        '- "Buy it?".',
        "The leaves moved.",
    ]


def test_unterminated_dialogue_line_continues_on_next_page(make_pdf):
    doc = make_pdf([
        SyntheticPage([Item(99, 100, '- "I will go to the')]),
        SyntheticPage([Item(88, 100, 'market tomorrow," he said.')]),
    ])
    assert _extract(doc).paragraphs == ['- "I will go to the market tomorrow," he said.']


def test_unterminated_dialogue_mid_page_stays_its_own_paragraph(make_pdf):
    # page 378: '... phán: "Tiền của ngươi đây, còn vợ thì phú về"1' ends a
    # paragraph mid-page without terminal punctuation; the next block is new prose.
    doc = make_pdf([SyntheticPage([
        Item(99, 100, "He ruled: - Take your money back"),
        Item(99, 130, "Another tale tells it differently."),
    ])])
    assert _extract(doc).paragraphs == [
        "He ruled:",
        "- Take your money back",
        "Another tale tells it differently.",
    ]


def test_bare_dash_mid_page_joins_next_block(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(99, 100, "He asked: -"),
        Item(88, 130, '"Buy it?".'),
    ])])
    assert _extract(doc).paragraphs == ["He asked:", '- "Buy it?".']


def test_unterminated_dialogue_is_not_glued_to_a_new_dialogue_turn(make_pdf):
    doc = make_pdf([
        SyntheticPage([Item(99, 100, '- "Wait,')]),
        SyntheticPage([Item(99, 100, '- "Go now."')]),
    ])
    assert _extract(doc).paragraphs == ['- "Wait,', '- "Go now."']


def test_pending_dialogue_is_flushed_at_story_end(make_pdf):
    doc = make_pdf([SyntheticPage([Item(99, 100, "He asked: -")])])
    assert _extract(doc).paragraphs == ["He asked:", "-"]


def test_terminated_dialogue_is_unchanged(make_pdf):
    doc = make_pdf([
        SyntheticPage([Item(99, 100, '- "Done."')]),
        SyntheticPage([Item(99, 100, "Then he left.")]),
    ])
    assert _extract(doc).paragraphs == ['- "Done."', "Then he left."]


# --- verse ------------------------------------------------------------------


def test_indented_italic_lines_become_verse_in_place(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(99, 100, "The bird cried out:"),
        Item(280, 130, "Cuckoo cuckoo.", "tiit"),
        Item(283, 150, "Rice is ripe,", "tiit"),
        Item(99, 180, "After that it flew away."),
    ])])
    assert _extract(doc).paragraphs == [
        "The bird cried out:",
        Verse(["Cuckoo cuckoo.", "Rice is ripe,"]),
        "After that it flew away.",
    ]


def test_verse_continuing_over_page_break_is_one_block(make_pdf):
    doc = make_pdf([
        SyntheticPage([Item(99, 100, "He sang:"), Item(280, 130, "Line one,", "tiit")]),
        SyntheticPage([Item(280, 100, "Line two.", "tiit"), Item(99, 130, "Then silence.")]),
    ])
    assert _extract(doc).paragraphs == [
        "He sang:",
        Verse(["Line one,", "Line two."]),
        "Then silence.",
    ]


def test_verse_after_pending_bare_dash_takes_the_dash(make_pdf):
    # The book itself sets dialogue dashes on verse lines ("- Tôi thề có trời
    # xanh nước biếc," on page 105), so a dash left open before verse opens it.
    doc = make_pdf([
        SyntheticPage([Item(99, 100, "She sang: -")]),
        SyntheticPage([Item(280, 100, "Oh my love,", "tiit")]),
    ])
    assert _extract(doc).paragraphs == ["She sang:", Verse(["- Oh my love,"])]


def test_verse_after_pending_unterminated_text_flushes_it_first(make_pdf):
    doc = make_pdf([
        SyntheticPage([Item(99, 100, '- "Listen to this,')]),
        SyntheticPage([Item(280, 100, "Oh my love,", "tiit")]),
    ])
    assert _extract(doc).paragraphs == ['- "Listen to this,', Verse(["Oh my love,"])]


def test_verse_inside_footnote_is_collected(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(99, 100, "Body text."),
        Item(88, 705, "1 A folk song says:", size=FOOTNOTE_SIZE),
        Item(253, 720, "Two of us like birds.", "tiit", FOOTNOTE_SIZE),
    ], separator_y=690)])
    story = _extract(doc)
    assert story.paragraphs == ["Body text."]
    assert story.footnotes[0].parts == ["A folk song says:", Verse(["Two of us like birds."])]


# --- real instances from data.pdf ------------------------------------------


@pytest.fixture(scope="module")
def section_iii_stories(data_pdf):
    return {s.story_number: s for s in StoryDiscoveryEngine.discover_stories(data_pdf, 255, 414)}


@pytest.fixture(scope="module")
def section_i_stories(data_pdf):
    return {s.story_number: s for s in StoryDiscoveryEngine.discover_stories(data_pdf, 86, 203)}


def _plain(paragraphs):
    return [p for p in paragraphs if isinstance(p, str)]


@pytest.mark.parametrize("number", [41, 42, 58])
def test_real_no_bare_dash_paragraphs(data_pdf, section_iii_stories, number):
    story = StoryExtractionEngine.extract_single_story(
        data_pdf, section_iii_stories[number], ExtractorConfig()
    )
    assert "-" not in _plain(story.paragraphs)
    assert "-" not in _plain(story.khao_di)


def test_real_story_41_mua_ha_on_one_line(data_pdf, section_iii_stories):
    story = StoryExtractionEngine.extract_single_story(
        data_pdf, section_iii_stories[41], ExtractorConfig()
    )
    text = _plain(story.paragraphs) + _plain(story.khao_di)
    assert '- "Mua hả?".' in text


def test_real_page_102_poem_is_verse_with_footnote_marker(data_pdf, section_i_stories):
    story_def = next(s for s in section_i_stories.values() if s.start_page <= 102 <= s.end_page)
    story = StoryExtractionEngine.extract_single_story(data_pdf, story_def, ExtractorConfig())
    verses = [p for p in story.paragraphs + story.khao_di if isinstance(p, Verse)]
    assert Verse(["Cô hố cô hố.", "Lúa đã trổ,", "Đỗ đã chín,", "Bay về mà ăn![^2]"]) in verses
