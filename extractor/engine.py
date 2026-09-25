"""
Story Content Extraction Engine.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
import fitz  # PyMuPDF

from .models import ExtractorConfig, Paragraph, StoryContent, StoryDefinition, Verse
from .normalizer import TextNormalizer
from .geometry import PdfGeometryHelper
from .footnotes import FootnoteEngine
from .discovery import StoryDiscoveryEngine
from .verse import VerseDetector


class StoryExtractionEngine:
    """Extracts body text, dialogues, verse, KHẢO DỊ section, and footnotes for a story."""

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

        paragraphs: List[Paragraph] = []
        khao_di_paragraphs: List[Paragraph] = []
        in_khao_di = False
        current_para_lines: List[str] = []
        # A dialogue item left open at the end of a block: a bare "-" anywhere,
        # or text without terminal punctuation at the foot of a page. Carried
        # across blocks *and pages* and prepended to the next text, so a dash at
        # the foot of one page stays on the same line as the speech that opens
        # the next page. (Mid-page, a block ending unterminated is a paragraph
        # end — blocks are paragraphs — so only the bare dash is held there.)
        pending_dialogue: Optional[str] = None

        def target() -> List[Paragraph]:
            return khao_di_paragraphs if in_khao_di else paragraphs

        def flush_current_paragraph():
            nonlocal current_para_lines
            if not current_para_lines:
                return

            para_text = TextNormalizer.clean_spaces(' '.join(current_para_lines))
            if para_text:
                target().extend(TextNormalizer.split_dialogues(para_text))
            current_para_lines = []

        def flush_pending_dialogue():
            nonlocal pending_dialogue
            if pending_dialogue is not None:
                target().append(pending_dialogue)
                pending_dialogue = None

        def add_verse_lines(verse_lines: List[str]):
            nonlocal pending_dialogue
            flush_current_paragraph()
            if pending_dialogue == '-':
                # The book sets dialogue dashes on verse lines itself
                # ("- Tôi thề có trời xanh nước biếc,"), so an open dash opens the verse.
                verse_lines = [f"- {verse_lines[0]}"] + verse_lines[1:]
                pending_dialogue = None
            flush_pending_dialogue()
            out = target()
            if out and isinstance(out[-1], Verse):
                out[-1].lines.extend(verse_lines)
            else:
                out.append(Verse(list(verse_lines)))

        def add_prose_block(text: str, pno: int, at_page_end: bool):
            nonlocal in_khao_di, current_para_lines, pending_dialogue

            # Skip Roman section header or Story Title block on start page
            if pno == story_def.start_page - 1:
                if StoryDiscoveryEngine.clean_category_title(text):
                    return
                if StoryDiscoveryEngine.clean_story_title(text):
                    return

            # Check for KHẢO DỊ section header
            if text.strip().upper() == 'KHẢO DỊ':
                flush_current_paragraph()
                flush_pending_dialogue()
                in_khao_di = True
                return

            # Skip scene dividers (* or * * *)
            if PdfGeometryHelper.is_scene_divider(text):
                flush_current_paragraph()
                flush_pending_dialogue()
                return

            if pending_dialogue is not None:
                if not text.startswith('-'):
                    text = f"{pending_dialogue} {text}"
                elif pending_dialogue != '-':
                    # A new dialogue turn: the open line ends where it is.
                    flush_pending_dialogue()
                # (a bare open dash followed by a dash-led turn is the same dash)
                pending_dialogue = None

            # Check if block is a dialogue or numbered point
            is_dialogue = (
                text.startswith('-')
                or ': -' in text
                or '. -' in text
            )
            is_numbered_point = bool(re.match(r'^\d+\.\s+', text))

            if is_dialogue or is_numbered_point:
                flush_current_paragraph()
                items = TextNormalizer.split_dialogues(text)
                if items and (items[-1] == '-' or (
                        at_page_end and not TextNormalizer.ends_sentence(items[-1]))):
                    pending_dialogue = items.pop()
                target().extend(items)
            else:
                if current_para_lines:
                    prev_text = current_para_lines[-1]
                    if not TextNormalizer.ends_sentence(prev_text):
                        current_para_lines.append(text)
                    else:
                        flush_current_paragraph()
                        current_para_lines = [text]
                else:
                    current_para_lines = [text]

        for pno in range(story_def.start_page - 1, story_def.end_page):
            page = doc[pno]
            h_sep_y = PdfGeometryHelper.find_footer_separator_y(page)
            body_max_y = PdfGeometryHelper.body_max_y(h_sep_y, config.footer_fallback_y)

            blocks = page.get_text('dict').get('blocks', [])
            blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))
            VerseDetector.mark_verse_lines(blocks, config)

            # Valid body text lines with inline footnote superscripts, grouped
            # per block into consecutive runs of prose / verse lines.
            page_runs: List[Tuple[bool, List[str]]] = []

            for b in blocks:
                if b.get('type') != 0:
                    continue

                runs: List[Tuple[bool, List[str]]] = []

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
                    if not clean_line:
                        continue
                    is_verse = bool(l.get('is_verse'))
                    if runs and runs[-1][0] == is_verse:
                        runs[-1][1].append(clean_line)
                    else:
                        runs.append((is_verse, [clean_line]))

                page_runs.extend(runs)

            for i, (is_verse, run_lines) in enumerate(page_runs):
                if is_verse:
                    add_verse_lines(run_lines)
                else:
                    add_prose_block(' '.join(run_lines), pno, at_page_end=i == len(page_runs) - 1)

        flush_current_paragraph()
        flush_pending_dialogue()

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
