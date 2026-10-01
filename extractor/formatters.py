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
            lines.append(f"# {story.category_heading or story.category}\n")
        if story.title:
            lines.append(f"## {story.story_number}. {story.heading_title or story.title}\n")

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
        pages = f"{fn.page}-{fn.end_page}" if fn.end_page and fn.end_page != fn.page else f"{fn.page}"
        prefix = f"[^{fn.orig_num}]: (Trang {pages})"
        if not fn.parts:
            return f"{prefix} {fn.text}" if fn.text else prefix
        parts = list(fn.parts)
        head = parts.pop(0) if isinstance(parts[0], str) else ""
        blocks = [f"{prefix} {head}" if head else prefix]
        for part in parts:
            rendered = MarkdownRenderer.render_paragraph(part)
            blocks.append("\n".join(f"    {line}" for line in rendered.split("\n")))
        return "\n\n".join(blocks)


class TableOfContentsBuilder:
    """Builds hierarchical Table of Contents JSON data structure."""

    BOOK_TITLE = 'KHO TÀNG TRUYỆN CỔ TÍCH VIỆT-NAM'

    @staticmethod
    def build(
        sections_map: Dict[str, List[Dict[str, any]]],
        total: int,
        range_str: str,
        leaf_key: str = "stories",
    ) -> Dict[str, any]:
        """Section manifest: each section title mapped to its leaves.

        ``leaf_key`` names the leaf kind — ``stories`` (Part 2) or ``essays``
        (Parts 1 and 3) — giving ``total_<leaf_key>`` and ``sections[].<leaf_key>``.
        """
        sections_list = []
        for sec_title, leaves in sections_map.items():
            sec_id_match = re.match(r'^([IVXLCDM]+)\.', sec_title)
            sec_id = sec_id_match.group(1) if sec_id_match else "OTHER"
            sections_list.append({
                'section_id': sec_id,
                'section_title': sec_title,
                leaf_key: leaves
            })

        return {
            'book_title': TableOfContentsBuilder.BOOK_TITLE,
            'extracted_range': range_str,
            f'total_{leaf_key}': total,
            'sections': sections_list
        }
