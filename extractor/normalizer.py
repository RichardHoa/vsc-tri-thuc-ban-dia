"""
Text Normalization & Cleaning for Vietnamese Folk Tales.
"""

from __future__ import annotations

import re
from typing import List


class TextNormalizer:
    """Handles Vietnamese encoding normalization, typography, and dialogue formatting."""

    LEGACY_ENCODING_MAP = {
        'ñ': 'đ',
        'Ñ': 'Đ',
        'Ð': 'Đ',
        "''": '"',
        '``': '"',
        '’’': '"',
        '‘‘': '"',
        '«': '"',
        '»': '"',
        '\xa0': ' ',  # Non-breaking space
        '\xad': '',   # Soft hyphen
        '\u200b': '', # Zero-width space
    }

    PUNCTUATION_ENDS = re.compile(r'[.!?:;…]["”\']?(\[\^\d+\])?$')
    HYPHENATED_WORD_BREAK = re.compile(r'(\w+)-\s+(\w+)')
    PUNCTUATION_SPACING = re.compile(r' +([,.;:!?])')
    QUOTE_LEFT_SPACING = re.compile(r'“\s+')
    QUOTE_RIGHT_SPACING = re.compile(r'\s+”')
    DIALOGUE_TRANSITION = re.compile(r'([:.]\s*)-\s*')
    DIALOGUE_WITH_NARRATIVE = re.compile(r'(["”\'][.!?]?|[.!?]["”\'])\s+([A-ZÀ-Ỵ])')

    @classmethod
    def normalize_encoding(cls, text: str) -> str:
        """Fix legacy encoding artifacts in the PDF text layer."""
        for src, dest in cls.LEGACY_ENCODING_MAP.items():
            text = text.replace(src, dest)
        return text

    @classmethod
    def clean_spaces(cls, text: str) -> str:
        """Normalize whitespace, clean punctuation spacing, and hyphenated line breaks."""
        text = cls.normalize_encoding(text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = cls.PUNCTUATION_SPACING.sub(r'\1', text)
        text = cls.QUOTE_LEFT_SPACING.sub('“', text)
        text = cls.QUOTE_RIGHT_SPACING.sub('”', text)
        text = cls.HYPHENATED_WORD_BREAK.sub(r'\1-\2', text)

        if text.startswith('-') and not text.startswith('- '):
            text = '- ' + text[1:].lstrip()

        return text.strip()

    @classmethod
    def is_all_caps(cls, text: str) -> bool:
        """Checks if a string contains letters and all letters are uppercase in Unicode."""
        letters = [c for c in text if c.isalpha()]
        return bool(letters) and all(c.isupper() for c in letters)

    @classmethod
    def split_dialogues(cls, text: str) -> List[str]:
        """
        Normalizes quotes and splits text containing dialogues so each dialogue line
        becomes its own standalone paragraph.
        """
        text = cls.clean_spaces(text)
        if not text:
            return []

        # Separate dialogue starts (': - ' or '. - ' -> ':\n- ' or '.\n- ')
        text = cls.DIALOGUE_TRANSITION.sub(r'\1\n- ', text)

        result_lines: List[str] = []
        for line in text.split('\n'):
            line = cls.clean_spaces(line)
            if not line:
                continue

            if line.startswith('-'):
                # Split dialogue ending followed by narrative sentence
                split_content = cls.DIALOGUE_WITH_NARRATIVE.sub(r'\1\n\2', line)
                for sub_line in split_content.split('\n'):
                    sub_line = cls.clean_spaces(sub_line)
                    if sub_line:
                        result_lines.append(sub_line)
            else:
                result_lines.append(line)

        return result_lines

    @classmethod
    def ends_sentence(cls, text: str) -> bool:
        """Determines if a paragraph ends with terminal punctuation."""
        return bool(cls.PUNCTUATION_ENDS.search(text.strip()))
