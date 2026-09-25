"""
Story Content Extraction Engine.
"""

from __future__ import annotations

import re
from typing import List
import fitz  # PyMuPDF

from .models import ExtractorConfig, StoryContent, StoryDefinition
from .normalizer import TextNormalizer
from .geometry import PdfGeometryHelper
from .footnotes import FootnoteEngine
from .discovery import StoryDiscoveryEngine


class StoryExtractionEngine:
    """Extracts body text, dialogues, KHẢO DỊ section, and footnotes for a story."""

    @staticmethod
    def extract_single_story(
        doc: fitz.Document,
        story_def: StoryDefinition,
        config: ExtractorConfig
    ) -> StoryContent:
        """Executes full single-story extraction pipeline with scoped footnote linking."""
        page_footnotes, all_footnotes = FootnoteEngine.collect_story_footnotes(
            doc, story_def.start_page, story_def.end_page, config
        )

        paragraphs: List[str] = []
        khao_di_paragraphs: List[str] = []
        in_khao_di = False
        current_para_lines: List[str] = []

        def flush_current_paragraph():
            nonlocal current_para_lines, in_khao_di
            if not current_para_lines:
                return

            para_text = TextNormalizer.clean_spaces(' '.join(current_para_lines))
            if para_text:
                for line in TextNormalizer.split_dialogues(para_text):
                    if in_khao_di:
                        khao_di_paragraphs.append(line)
                    else:
                        paragraphs.append(line)
            current_para_lines = []

        for pno in range(story_def.start_page - 1, story_def.end_page):
            page_num = pno + 1
            page = doc[pno]
            h_sep_y = PdfGeometryHelper.find_footer_separator_y(page)
            body_max_y = PdfGeometryHelper.body_max_y(h_sep_y, config.footer_fallback_y)

            blocks = page.get_text('dict').get('blocks', [])
            blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))

            for b in blocks:
                if b.get('type') != 0:
                    continue

                # Collect valid body text lines with inline footnote superscripts
                block_lines: List[str] = []

                for l in b.get('lines', []):
                    line_y0 = l['bbox'][1]
                    raw_line_text = ''.join(s['text'] for s in l.get('spans', []))

                    # Filter running headers and footers/footnotes at line level
                    if PdfGeometryHelper.is_header_line(line_y0, config.min_header_y):
                        continue
                    if PdfGeometryHelper.is_footer_line(
                        line_y0, raw_line_text, h_sep_y, config.max_footer_y, config.footer_fallback_y
                    ):
                        continue

                    line_text = ""
                    for s in l.get('spans', []):
                        stext = TextNormalizer.normalize_encoding(s['text'])

                        # Footnote superscript detection
                        if (s['size'] < config.superscript_max_font_size
                                and stext.strip().isdigit() and line_y0 < body_max_y):
                            fn_num = stext.strip()
                            line_text += f"[^{fn_num}]"
                        else:
                            line_text += stext

                    clean_line = TextNormalizer.clean_spaces(line_text)
                    if clean_line:
                        block_lines.append(clean_line)

                if not block_lines:
                    continue

                combined_block_text = ' '.join(block_lines)

                # Skip Roman section header or Story Title block on start page
                if pno == story_def.start_page - 1:
                    if StoryDiscoveryEngine.clean_category_title(combined_block_text):
                        continue
                    if StoryDiscoveryEngine.clean_story_title(combined_block_text):
                        continue

                # Check for KHẢO DỊ section header
                if combined_block_text.strip().upper() == 'KHẢO DỊ':
                    flush_current_paragraph()
                    in_khao_di = True
                    continue

                # Skip scene dividers (* or * * *)
                if PdfGeometryHelper.is_scene_divider(combined_block_text):
                    flush_current_paragraph()
                    continue

                # Check if block is a dialogue or numbered point
                is_dialogue = (
                    combined_block_text.startswith('-')
                    or ': -' in combined_block_text
                    or '. -' in combined_block_text
                )
                is_numbered_point = bool(re.match(r'^\d+\.\s+', combined_block_text))

                if is_dialogue or is_numbered_point:
                    flush_current_paragraph()
                    for item in TextNormalizer.split_dialogues(combined_block_text):
                        if in_khao_di:
                            khao_di_paragraphs.append(item)
                        else:
                            paragraphs.append(item)
                else:
                    if current_para_lines:
                        prev_text = current_para_lines[-1]
                        if not TextNormalizer.ends_sentence(prev_text):
                            current_para_lines.append(combined_block_text)
                        else:
                            flush_current_paragraph()
                            current_para_lines = [combined_block_text]
                    else:
                        current_para_lines = [combined_block_text]

        flush_current_paragraph()

        return StoryContent(
            category=story_def.category,
            story_number=story_def.story_number,
            title=story_def.title,
            start_page=story_def.start_page,
            end_page=story_def.end_page,
            paragraphs=paragraphs,
            khao_di=khao_di_paragraphs,
            footnotes=all_footnotes
        )
