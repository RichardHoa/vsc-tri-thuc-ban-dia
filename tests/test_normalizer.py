"""TextNormalizer helpers used by the dialogue page-boundary fix."""

from __future__ import annotations

from extractor.normalizer import TextNormalizer


def test_split_dialogues_leaves_bare_trailing_dash():
    assert TextNormalizer.split_dialogues("Ngốc hỏi: -") == ["Ngốc hỏi:", "-"]


def test_ends_sentence_marks_open_dialogue():
    # The engine holds a dialogue item that doesn't end a sentence and joins it
    # to the next text, so these decide what counts as "left open".
    assert not TextNormalizer.ends_sentence("-")
    assert not TextNormalizer.ends_sentence('- "Tôi sẽ đi')
    assert TextNormalizer.ends_sentence('- "Mua hả?".')
    assert TextNormalizer.ends_sentence("Ngốc hỏi:")
    assert TextNormalizer.ends_sentence('- "Giả tiền đây!"')
