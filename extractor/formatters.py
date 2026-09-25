"""
Markdown Renderer and Table of Contents Builder.
"""

from __future__ import annotations

import re
from typing import Dict, List

from .models import Footnote, Paragraph, StoryContent, Verse


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
            lines.append(f"{MarkdownRenderer.render_paragraph(p)}\n")

        if story.khao_di:
            lines.append("### KHẢO DỊ\n")
            for p in story.khao_di:
                lines.append(f"{MarkdownRenderer.render_paragraph(p)}\n")

        if story.footnotes:
            lines.append("---\n")
            lines.append("### Chú thích\n")
            for fn in story.footnotes:
                lines.append(f"{MarkdownRenderer.render_footnote(fn)}\n")

        return "\n".join(lines)

    @staticmethod
    def render_paragraph(p: Paragraph) -> str:
        """Prose as-is; verse as a blockquote with one ``> `` line per verse line."""
        if isinstance(p, Verse):
            return "\n".join(f"> {line}" for line in p.lines)
        return p

    @staticmethod
    def render_footnote(fn: Footnote) -> str:
        """``[^N]: (Trang P) text``; an entry with verse continues as indented blocks."""
        prefix = f"[^{fn.orig_num}]: (Trang {fn.page})"
        if not fn.parts:
            return f"{prefix} {fn.text}"
        parts = list(fn.parts)
        head = parts.pop(0) if isinstance(parts[0], str) else ""
        blocks = [f"{prefix} {head}" if head else prefix]
        for part in parts:
            rendered = MarkdownRenderer.render_paragraph(part)
            blocks.append("\n".join(f"    {line}" for line in rendered.split("\n")))
        return "\n\n".join(blocks)


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
