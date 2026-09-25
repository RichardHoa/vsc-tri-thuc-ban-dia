"""TextNormalizer helpers used by the dialogue page-boundary fix."""

from __future__ import annotations

from extractor.normalizer import TextNormalizer


def test_split_dialogues_leaves_bare_trailing_dash():
    assert TextNormalizer.split_dialogues("Ngốc hỏi: -") == ["Ngốc hỏi:", "-"]


def test_is_open_dialogue():
    assert TextNormalizer.is_open_dialogue("-")
    assert TextNormalizer.is_open_dialogue('- "Tôi sẽ đi')
    assert not TextNormalizer.is_open_dialogue('- "Mua hả?".')
    assert not TextNormalizer.is_open_dialogue("Ngốc hỏi:")
    assert not TextNormalizer.is_open_dialogue('- "Giả tiền đây!"')
    assert not TextNormalizer.is_open_dialogue("")
