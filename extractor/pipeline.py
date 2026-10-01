"""
High-level Batch Pipeline for Folk Story Extraction.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
import fitz  # PyMuPDF

from .models import ExtractorConfig, StoryDefinition
from .discovery import PartLayoutDiscovery, StoryDiscoveryEngine
from .engine import StoryExtractionEngine
from .formatters import MarkdownRenderer, TableOfContentsBuilder
from .toc import PartRange, SectionRange, TableOfContentsParser


def _write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


class BookPipeline:
    """Extracts the whole book (or a ``--part`` / ``--section`` selection) into
    the Part → Section → leaf layout::

        <output_dir>/table_of_contents.json            root manifest (whole tree)
        <output_dir>/<PART>/introduction.md            Parts 2 and 3
        <output_dir>/<PART>/<ROMAN>_<SLUG>/            story_NNN.md or essay_NN.md
                                                       + table_of_contents.json

    Stories go through ``FolkStoryPipeline`` per Section; Essays and
    Introductions are bounded by ``PartLayoutDiscovery``.
    """

    INTRODUCTION_FILE = "introduction.md"
    MANIFEST_FILE = "table_of_contents.json"

    def __init__(
        self,
        pdf_path: str,
        output_dir: str,
        part: Optional[int] = None,
        section_spec: Optional[str] = None,
        story_number: Optional[int] = None,
        verbose: bool = False,
    ):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.part = part
        self.section_spec = section_spec
        self.story_number = story_number
        self.verbose = verbose

    def _config(self, **overrides) -> ExtractorConfig:
        return ExtractorConfig(pdf_path=self.pdf_path, verbose=self.verbose, **overrides)

    def run(self) -> Dict[str, Any]:
        """Extracts the selection and rewrites the root manifest."""
        part = self.part
        if self.story_number is not None:
            if part not in (None, 2):
                raise ValueError("--story selects a Part 2 Story; it cannot be combined with --part "
                                 f"{part}.")
            part = 2
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

        with fitz.open(self.pdf_path) as doc:
            parts = TableOfContentsParser.parse_parts(doc)
            selection = TableOfContentsParser.select_parts(parts, part, self.section_spec)
            for part_range, sections in selection:
                self._run_part(doc, part_range, sections)

        root = self.build_root_manifest(parts, self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        _write_json(os.path.join(self.output_dir, self.MANIFEST_FILE), root)
        return root

    def _run_part(self, doc: fitz.Document, part: PartRange, sections: List[SectionRange]) -> None:
        print(f"== Part {part.number}: {part.full_title} (pages {part.start_page}-{part.end_page})")
        part_dir = os.path.join(self.output_dir, part.folder_name)
        os.makedirs(part_dir, exist_ok=True)
        if self.story_number is not None:
            layout = None  # a single Story: no Introduction, no Essays
        else:
            layout = PartLayoutDiscovery.discover(doc, part, self._config())
            if self.section_spec is None and layout.introduction is not None:
                self._write_leaf(doc, layout.introduction,
                                 os.path.join(part_dir, self.INTRODUCTION_FILE))

        for section in sections:
            print(f"== Section {section.index}: {section.full_title} "
                  f"(pages {section.start_page}-{section.end_page})")
            section_dir = os.path.join(self.output_dir, section.path)
            if part.leaf_kind == "stories":
                FolkStoryPipeline(self._config(
                    start_page=section.start_page,
                    end_page=section.end_page,
                    output_dir=section_dir,
                    story_number=self.story_number,
                    hard_stops=section.hard_stops + [section.end_page + 1],
                )).run()
            else:
                self._write_essays(doc, section, layout.essays.get(section.roman, []), section_dir)

    def _write_leaf(self, doc: fitz.Document, leaf: StoryDefinition, path: str):
        content = StoryExtractionEngine.extract_single_story(doc, leaf, self._config())
        with open(path, 'w', encoding='utf-8') as f:
            f.write(MarkdownRenderer.render(content))
        return content

    def _write_essays(
        self, doc: fitz.Document, section: SectionRange, essays: List[StoryDefinition], section_dir: str
    ) -> None:
        os.makedirs(section_dir, exist_ok=True)
        entries = []
        for essay in essays:
            logging.info(f"Extracting Essay {section.roman}.{essay.story_number}: {essay.title} "
                         f"(Pages {essay.start_page} - {essay.end_page})...")
            md_filename = f"essay_{essay.story_number:02d}.md"
            content = self._write_leaf(doc, essay, os.path.join(section_dir, md_filename))
            entries.append({
                'essay_number': essay.story_number,
                'title': essay.title,
                'start_page': essay.start_page,
                'end_page': essay.end_page,
                'markdown_file': md_filename,
                'footnote_count': len(content.footnotes),
            })
        end = max([e.end_page for e in essays], default=section.end_page)
        toc = TableOfContentsBuilder.build(
            {section.full_title: entries}, len(entries), f"{section.start_page} - {end}", leaf_key="essays"
        )
        _write_json(os.path.join(section_dir, self.MANIFEST_FILE), toc)

    @classmethod
    def build_root_manifest(cls, parts: List[PartRange], output_dir: str) -> Dict[str, Any]:
        """The full Part → Section → leaf tree.

        Leaves are read back from each Section's manifest on disk, so a partial
        run still yields the whole tree; a Section not extracted yet has none.
        """
        out_parts = []
        for part in parts:
            intro = f"{part.folder_name}/{cls.INTRODUCTION_FILE}"
            sections = []
            for section in part.sections:
                leaves: List[Dict[str, Any]] = []
                manifest = os.path.join(output_dir, section.path, cls.MANIFEST_FILE)
                if os.path.exists(manifest):
                    with open(manifest, encoding='utf-8') as f:
                        for sec in json.load(f).get('sections', []):
                            leaves.extend(sec.get(part.leaf_kind, []))
                sections.append({
                    'section_id': section.roman,
                    'section_title': section.full_title,
                    'folder': section.path,
                    'start_page': section.start_page,
                    'end_page': section.end_page,
                    part.leaf_kind: leaves,
                })
            out_parts.append({
                'part_id': part.folder_name,
                'part_number': part.number,
                'part_title': part.full_title,
                'start_page': part.start_page,
                'end_page': part.end_page,
                'introduction': intro if os.path.exists(os.path.join(output_dir, intro)) else None,
                'sections': sections,
            })
        return {'book_title': TableOfContentsBuilder.BOOK_TITLE, 'parts': out_parts}
