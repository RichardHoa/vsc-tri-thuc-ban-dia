"""
High-level Batch Pipeline for Folk Story Extraction.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, List
import fitz  # PyMuPDF

from .models import ExtractorConfig
from .discovery import StoryDiscoveryEngine
from .engine import StoryExtractionEngine
from .formatters import MarkdownRenderer, TableOfContentsBuilder


class FolkStoryPipeline:
    """High-level pipeline orchestrating discovery, extraction, formatting, and file export."""

    def __init__(self, config: ExtractorConfig):
        self.config = config
        self._setup_logging()

    def _setup_logging(self):
        log_level = logging.DEBUG if self.config.verbose else logging.INFO
        logging.basicConfig(
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
            level=log_level
        )

    def run(self) -> Dict[str, any]:
        """Executes full extraction pipeline."""
        if not os.path.exists(self.config.pdf_path):
            raise FileNotFoundError(f"PDF file not found: {self.config.pdf_path}")

        os.makedirs(self.config.output_dir, exist_ok=True)

        with fitz.open(self.config.pdf_path) as doc:
            logging.info(
                f"Discovering stories between page {self.config.start_page} and {self.config.end_page}..."
            )
            stories = StoryDiscoveryEngine.discover_stories(
                doc, self.config.start_page, self.config.end_page
            )

            if self.config.story_number is not None:
                stories = [s for s in stories if s.story_number == self.config.story_number]
                if not stories:
                    logging.warning(f"Story #{self.config.story_number} was not found in page range.")
                    return {}

            for s in stories:
                for stop in self.config.hard_stops:
                    if s.start_page < stop <= s.end_page:
                        s.end_page = stop - 1

            logging.info(f"Discovered {len(stories)} stories.")

            sections_map: Dict[str, List[Dict[str, any]]] = {}
            actual_max_page = self.config.start_page

            for story_def in stories:
                cat = story_def.category
                if cat not in sections_map:
                    sections_map[cat] = []

                logging.info(
                    f"Extracting Story #{story_def.story_number:03d}: {story_def.title} "
                    f"(Pages {story_def.start_page} - {story_def.end_page})..."
                )

                story_content = StoryExtractionEngine.extract_single_story(
                    doc, story_def, self.config
                )
                actual_max_page = max(actual_max_page, story_content.end_page)

                md_filename = f"story_{story_def.story_number:03d}.md"
                md_path = os.path.join(self.config.output_dir, md_filename)
                md_text = MarkdownRenderer.render(story_content)

                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md_text)

                sections_map[cat].append({
                    'story_number': story_def.story_number,
                    'title': story_def.title,
                    'start_page': story_content.start_page,
                    'end_page': story_content.end_page,
                    'markdown_file': md_filename,
                    'has_khao_di': len(story_content.khao_di) > 0,
                    'footnote_count': len(story_content.footnotes)
                })

            toc_range = f"{self.config.start_page} - {actual_max_page}"
            toc_data = TableOfContentsBuilder.build(sections_map, len(stories), toc_range)
            toc_path = os.path.join(self.config.output_dir, "table_of_contents.json")

            with open(toc_path, 'w', encoding='utf-8') as f:
                json.dump(toc_data, f, ensure_ascii=False, indent=2)

            logging.info("Extraction complete!")
            logging.info(f"- Total stories extracted: {len(stories)}")
            logging.info(f"- Table of contents: {toc_path}")
            logging.info(f"- Output directory: {self.config.output_dir}")

            return toc_data
