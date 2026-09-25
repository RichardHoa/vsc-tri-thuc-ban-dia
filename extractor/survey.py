"""
Edge-Case Survey.

Read-only scan of a PDF page range for the layout patterns the extractor has to
handle specially, reported per page:

* **Poem candidates** — runs of verse lines (see :mod:`extractor.verse`), in the
  body or the footnote area.
* **Long-footnote spans** — a footnote that carries over a page break (the next
  page's footnote area opens with unnumbered text), and — separately — a footnote
  *number* that recurs on many nearby pages because footnotes renumber per page.
* **Dialogue page-boundary breaks** — a text block (usually a page's last body
  line) ending in a dialogue-opening dash with the quoted speech on a later page.

Also records per-range layout statistics (body margin, paragraph indent, italic
font names) so the verse signal can be confirmed to hold book-wide.

The same detection is reused elsewhere: :class:`extractor.verse.VerseDetector`
by the extraction engine and footnote parser, and
:meth:`EdgeCaseSurvey.find_footnote_chains` by the validator's footnote-chain
completeness check. Like the rest of ``extractor/`` this never mutates the PDF.
"""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from .discovery import StoryDiscoveryEngine
from .footnotes import FootnoteEngine
from .geometry import PdfGeometryHelper
from .models import ExtractorConfig, StoryDefinition
from .verse import VerseDetector

#: A dash (preceded by start, space or punctuation) as the last thing on a line.
OPEN_DASH_END = re.compile(r'(?:^|[\s:.,;!?"”])[-–]\s*$')

#: A recurring footnote number is reported once it spans at least this many
#: pages with no more than RECURRING_MAX_GAP pages between appearances.
RECURRING_MIN_PAGES = 8
RECURRING_MAX_GAP = 3


@dataclass
class PoemRun:
    page: int
    region: str  # "body" | "footnote"
    x0: float
    lines: List[str]
    fonts: List[str]
    story: Optional[int] = None


@dataclass
class DialogueBreak:
    page: int
    kind: str  # "page_end" | "block_end"
    text: str
    story: Optional[int] = None


@dataclass
class FootnoteChain:
    """One footnote spread over consecutive pages (``pages[0]`` holds its number)."""
    num: int
    pages: List[int]
    snippet: str


@dataclass
class RecurringFootnoteRun:
    """A footnote number reappearing on many nearby pages (per-page renumbering)."""
    num: int
    pages: List[int]


@dataclass
class LayoutStats:
    body_margin_x0: float = 0.0
    paragraph_indent_x0: float = 0.0
    italic_fonts: Dict[str, int] = field(default_factory=dict)
    verse_x0_range: Tuple[float, float] = (0.0, 0.0)


@dataclass
class RangeSurvey:
    label: str
    start_page: int
    end_page: int
    stories: List[StoryDefinition] = field(default_factory=list)
    poems: List[PoemRun] = field(default_factory=list)
    dialogue_breaks: List[DialogueBreak] = field(default_factory=list)
    footnote_chains: List[FootnoteChain] = field(default_factory=list)
    recurring_footnotes: List[RecurringFootnoteRun] = field(default_factory=list)
    stats: LayoutStats = field(default_factory=LayoutStats)


class EdgeCaseSurvey:
    """Scans PDF pages for poems, multi-page footnotes, and dialogue page breaks."""

    @staticmethod
    def _sorted_text_blocks(page: fitz.Page) -> List[dict]:
        blocks = [b for b in page.get_text('dict').get('blocks', []) if b.get('type') == 0]
        blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))
        return blocks

    @staticmethod
    def _region(line: dict, h_sep_y: Optional[float], config: ExtractorConfig) -> Optional[str]:
        """``"body"``, ``"footnote"``, or ``None`` for the running header / page number."""
        y0 = line['bbox'][1]
        text = VerseDetector.line_text(line)
        if PdfGeometryHelper.is_header_line(y0, config.min_header_y) or y0 > config.max_footer_y:
            return None
        if PdfGeometryHelper.is_footer_line(
            y0, text, h_sep_y, config.max_footer_y, config.footer_fallback_y
        ):
            return "footnote"
        return "body"

    @classmethod
    def find_poem_runs(cls, page: fitz.Page, page_num: int, config: ExtractorConfig) -> List[PoemRun]:
        h_sep_y = PdfGeometryHelper.find_footer_separator_y(page)
        blocks = cls._sorted_text_blocks(page)
        VerseDetector.mark_verse_lines(blocks, config)

        runs: List[PoemRun] = []
        current: Optional[PoemRun] = None
        for b in blocks:
            for line in b.get('lines', []):
                text = VerseDetector.line_text(line).strip()
                if not text:
                    continue
                region = cls._region(line, h_sep_y, config)
                if region is None or not line.get('is_verse'):
                    current = None
                    continue
                if current is None or current.region != region:
                    current = PoemRun(page=page_num, region=region, x0=line['bbox'][0], lines=[], fonts=[])
                    runs.append(current)
                current.x0 = min(current.x0, line['bbox'][0])
                current.lines.append(text)
                for span in line['spans']:
                    if VerseDetector.is_italic_font(span['font']) and span['font'] not in current.fonts:
                        current.fonts.append(span['font'])
        return runs

    @classmethod
    def find_dialogue_breaks(
        cls, page: fitz.Page, page_num: int, config: ExtractorConfig
    ) -> List[DialogueBreak]:
        h_sep_y = PdfGeometryHelper.find_footer_separator_y(page)
        block_ends: List[str] = []
        for b in cls._sorted_text_blocks(page):
            last = None
            for line in b.get('lines', []):
                text = VerseDetector.line_text(line).strip()
                if text and cls._region(line, h_sep_y, config) == "body":
                    last = text
            if last is not None:
                block_ends.append(last)

        breaks: List[DialogueBreak] = []
        for i, text in enumerate(block_ends):
            if OPEN_DASH_END.search(text):
                kind = "page_end" if i == len(block_ends) - 1 else "block_end"
                breaks.append(DialogueBreak(page=page_num, kind=kind, text=text))
        return breaks

    @staticmethod
    def find_footnote_chains(
        doc: fitz.Document, start_page: int, end_page: int, config: ExtractorConfig
    ) -> List[FootnoteChain]:
        """Footnotes that continue over a page break, detected from the raw footer.

        A page whose footnote area opens with unnumbered text, following a page
        that has footnotes, continues that page's open footnote. The chain's
        first page may lie before ``start_page`` when the range opens mid-chain.
        """
        chains: List[FootnoteChain] = []
        open_chain: Optional[FootnoteChain] = None
        prev_num = (
            FootnoteEngine.last_footnote_num(doc, start_page - 1, config) if start_page > 1 else None
        )
        for page_num in range(start_page, end_page + 1):
            entries = FootnoteEngine.page_entries(doc, page_num, config)
            if not entries:
                prev_num, open_chain = None, None
                continue
            head = entries[0]
            if head['continued'] and prev_num is not None:
                if open_chain is not None and open_chain.pages[-1] == page_num - 1:
                    open_chain.pages.append(page_num)
                else:
                    open_chain = FootnoteChain(num=prev_num, pages=[page_num - 1, page_num],
                                               snippet=head['text'][:80])
                    chains.append(open_chain)
            elif head['continued']:
                # Unnumbered text with nothing to continue: the parser's fallback
                # numbers it 1 (mirrors FootnoteEngine.collect_story_footnotes).
                prev_num = 1
            numbered = [e for e in entries if not e['continued']]
            if numbered:
                prev_num, open_chain = numbered[-1]['orig_num'], None
        return chains

    @staticmethod
    def find_recurring_footnote_runs(
        doc: fitz.Document,
        start_page: int,
        end_page: int,
        config: ExtractorConfig,
        min_pages: int = RECURRING_MIN_PAGES,
        max_gap: int = RECURRING_MAX_GAP,
    ) -> List[RecurringFootnoteRun]:
        pages_by_num: Dict[int, List[int]] = collections.defaultdict(list)
        for page_num in range(start_page, end_page + 1):
            for entry in FootnoteEngine.page_entries(doc, page_num, config):
                if not entry['continued'] and page_num not in pages_by_num[entry['orig_num']]:
                    pages_by_num[entry['orig_num']].append(page_num)

        runs: List[RecurringFootnoteRun] = []
        for num, pages in sorted(pages_by_num.items()):
            run: List[int] = []
            for page in pages + [None]:
                if page is not None and (not run or page - run[-1] <= max_gap):
                    run.append(page)
                    continue
                if len(run) >= min_pages:
                    runs.append(RecurringFootnoteRun(num=num, pages=run))
                run = [page] if page is not None else []
        return runs

    @classmethod
    def layout_stats(cls, doc: fitz.Document, start_page: int, end_page: int,
                     config: ExtractorConfig) -> LayoutStats:
        x0s: collections.Counter = collections.Counter()
        fonts: collections.Counter = collections.Counter()
        verse_x0: List[float] = []
        for pno in range(start_page - 1, end_page):
            page = doc[pno]
            blocks = cls._sorted_text_blocks(page)
            VerseDetector.mark_verse_lines(blocks, config)
            for b in blocks:
                for line in b.get('lines', []):
                    if not VerseDetector.line_text(line).strip():
                        continue
                    x0s[round(line['bbox'][0])] += 1
                    if line.get('is_verse'):
                        verse_x0.append(line['bbox'][0])
                    for span in line['spans']:
                        if VerseDetector.is_italic_font(span['font']) and span['text'].strip():
                            fonts[span['font']] += len(span['text'])
        common = [x for x, _ in x0s.most_common(2)]
        return LayoutStats(
            body_margin_x0=float(min(common)) if common else 0.0,
            paragraph_indent_x0=float(max(common)) if common else 0.0,
            italic_fonts=dict(fonts.most_common()),
            verse_x0_range=(min(verse_x0), max(verse_x0)) if verse_x0 else (0.0, 0.0),
        )

    @staticmethod
    def _story_at(stories: List[StoryDefinition], page: int) -> Optional[int]:
        # Adjacent stories share boundary pages; report the one that starts last.
        owner = None
        for s in stories:
            if s.start_page <= page <= s.end_page:
                owner = s.story_number
        return owner

    @classmethod
    def survey_range(
        cls,
        doc: fitz.Document,
        start_page: int,
        end_page: int,
        config: ExtractorConfig,
        label: str,
        hard_stops: Optional[List[int]] = None,
    ) -> RangeSurvey:
        stories = StoryDiscoveryEngine.discover_stories(doc, start_page, end_page)
        for s in stories:
            for stop in (hard_stops or []) + [end_page + 1]:
                if s.start_page < stop <= s.end_page:
                    s.end_page = stop - 1

        survey = RangeSurvey(label=label, start_page=start_page, end_page=end_page, stories=stories)
        for page_num in range(start_page, end_page + 1):
            page = doc[page_num - 1]
            for run in cls.find_poem_runs(page, page_num, config):
                run.story = cls._story_at(stories, page_num)
                survey.poems.append(run)
            for brk in cls.find_dialogue_breaks(page, page_num, config):
                brk.story = cls._story_at(stories, page_num)
                survey.dialogue_breaks.append(brk)
        survey.footnote_chains = cls.find_footnote_chains(doc, start_page, end_page, config)
        survey.recurring_footnotes = cls.find_recurring_footnote_runs(doc, start_page, end_page, config)
        survey.stats = cls.layout_stats(doc, start_page, end_page, config)
        return survey

    @staticmethod
    def _fmt_story(n: Optional[int]) -> str:
        return str(n) if n is not None else "— (non-story)"

    @classmethod
    def render_catalog(cls, surveys: List[RangeSurvey]) -> str:
        out: List[str] = ["# Edge-case catalog", ""]
        out.append(
            "Generated by `survey_data.py` (`extractor/survey.py`). One section per surveyed "
            "range. Story numbers are the owning story per `StoryDiscoveryEngine` "
            "(the later story on a shared boundary page)."
        )
        out.append("")
        out.append("| Range | Pages | Stories | Poem runs (body / footnote) | Footnote chains | "
                   "Recurring fn numbers | Dialogue breaks (page end / block end) |")
        out.append("|---|---|---|---|---|---|---|")
        for s in surveys:
            body = sum(1 for p in s.poems if p.region == "body")
            fn = len(s.poems) - body
            pe = sum(1 for d in s.dialogue_breaks if d.kind == "page_end")
            out.append(
                f"| {s.label} | {s.start_page}-{s.end_page} | {len(s.stories)} | {body} / {fn} | "
                f"{len(s.footnote_chains)} | {len(s.recurring_footnotes)} | "
                f"{pe} / {len(s.dialogue_breaks) - pe} |"
            )
        out.append("")

        for s in surveys:
            out.append(f"## {s.label} (pages {s.start_page}-{s.end_page})")
            out.append("")
            st = s.stats
            fonts = ", ".join(f"`{k}` ({v})" for k, v in st.italic_fonts.items()) or "none"
            out.append(
                f"Layout: body margin x0≈{st.body_margin_x0:.0f}, paragraph indent x0≈"
                f"{st.paragraph_indent_x0:.0f}; verse x0 range {st.verse_x0_range[0]:.0f}-"
                f"{st.verse_x0_range[1]:.0f}; italic fonts (chars): {fonts}."
            )
            out.append("")

            out.append("### Poem candidates")
            out.append("")
            if s.poems:
                out.append("| Page | Story | Region | x0 | Lines | First line | Fonts |")
                out.append("|---|---|---|---|---|---|---|")
                for p in s.poems:
                    first = p.lines[0].replace("|", "\\|")
                    out.append(
                        f"| {p.page} | {cls._fmt_story(p.story)} | {p.region} | {p.x0:.0f} | "
                        f"{len(p.lines)} | {first} | {', '.join(p.fonts)} |"
                    )
            else:
                out.append("- None.")
            out.append("")

            out.append("### Long-footnote spans")
            out.append("")
            out.append("Footnotes continued over a page break (continuation page opens unnumbered):")
            out.append("")
            if s.footnote_chains:
                for c in s.footnote_chains:
                    snippet = c.snippet.replace("|", "\\|")
                    out.append(f"- [^{c.num}] pages {c.pages} — continuation starts: “{snippet}”")
            else:
                out.append("- None.")
            out.append("")
            out.append(
                f"Footnote numbers recurring on ≥{RECURRING_MIN_PAGES} nearby pages "
                f"(gap ≤{RECURRING_MAX_GAP}; independent per-page footnotes, not one long note):"
            )
            out.append("")
            if s.recurring_footnotes:
                for r in s.recurring_footnotes:
                    out.append(f"- [^{r.num}] on {len(r.pages)} pages: {r.pages[0]}-{r.pages[-1]}")
            else:
                out.append("- None.")
            out.append("")

            out.append("### Dialogue page-boundary breaks")
            out.append("")
            if s.dialogue_breaks:
                out.append("| Page | Story | Kind | Block ends with |")
                out.append("|---|---|---|---|")
                for d in s.dialogue_breaks:
                    tail = d.text[-70:].replace("|", "\\|")
                    out.append(f"| {d.page} | {cls._fmt_story(d.story)} | {d.kind} | …{tail} |")
            else:
                out.append("- None.")
            out.append("")
        return "\n".join(out)
