"""
Markdown Renderer and Table of Contents Builder.
"""

from __future__ import annotations

import re
from typing import Dict, List

from .models import StoryContent


class MarkdownRenderer:
    """Renders structured StoryContent into clean GitHub-flavored Markdown."""

    @staticmethod
    def render(story: StoryContent) -> str:
        """Formats story, khảo dị, and footnote sections into Markdown."""
        lines: List[str] = []

        if story.category:
            lines.append(f"# {story.category}\n")
        if story.title:
            lines.append(f"## {story.story_number}. {story.title}\n")

        for p in story.paragraphs:
            lines.append(f"{p}\n")

        if story.khao_di:
            lines.append("### KHẢO DỊ\n")
            for p in story.khao_di:
                lines.append(f"{p}\n")

        if story.footnotes:
            lines.append("---\n")
            lines.append("### Chú thích\n")
            for fn in story.footnotes:
                lines.append(f"[^{fn.orig_num}]: (Trang {fn.page}) {fn.text}\n")

        return "\n".join(lines)


class TableOfContentsBuilder:
    """Builds hierarchical Table of Contents JSON data structure."""

    @staticmethod
    def build(
        sections_map: Dict[str, List[Dict[str, any]]],
        total_stories: int,
        range_str: str
    ) -> Dict[str, any]:
        """Constructs TOC dictionary mapping sections to extracted stories."""
        sections_list = []
        for sec_title, stories in sections_map.items():
            sec_id_match = re.match(r'^([IVXLCDM]+)\.', sec_title)
            sec_id = sec_id_match.group(1) if sec_id_match else "OTHER"
            sections_list.append({
                'section_id': sec_id,
                'section_title': sec_title,
                'stories': stories
            })

        return {
            'book_title': 'KHO TÀNG TRUYỆN CỔ TÍCH VIỆT-NAM',
            'extracted_range': range_str,
            'total_stories': total_stories,
            'sections': sections_list
        }
