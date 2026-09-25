"""
Extraction Accuracy Validator.

Read-only quality checks over already-extracted folk-story output. Never mutates
extraction results: it reads `table_of_contents.json` + `story_NNN.md` from a
section output directory, re-reads the raw PyMuPDF page text for each story's
page range, and scores text fidelity with `difflib`.

Two kinds of signal are produced:

* **Structural checks** — empty title/category/body, orphan footnote markers,
  orphan footnote entries, bare ``-`` paragraphs, footnote-chain gaps, low
  character density, section-level story-count drift.
* **Text alignment** — `rendered_coverage` (what fraction of the rendered Markdown
  prose is found in the raw PDF page text) is the primary metric and the report's
  sort key / threshold. It is scored **per segment**: the body prose is diffed
  against the story's full page range, and each footnote body is diffed against a
  window anchored to its own ``(Trang P)`` page, then the segments are combined
  length-weighted. This is required because ``MarkdownRenderer`` relocates every
  footnote body to an end-of-file block while the raw PDF keeps them interleaved
  per page; a whole-blob ``difflib`` diff is defeated by that reordering and
  reports false-low scores on footnote-heavy stories. `raw_coverage` is
  **informational only**: adjacent stories share PDF boundary pages, so a story's
  page range legitimately contains a neighbour's text and raw coverage is
  inherently noisy. It must never be used to fail or sort a story.

Memory is deliberately bounded: exactly one story's raw + rendered text is held at
a time, never a whole-section blob (`difflib.SequenceMatcher` is quadratic-ish).

Vietnamese correctness: both sides are normalized to Unicode NFC before comparison.
Diacritics are never stripped, folded, or casefolded.

## Future Extension (deferred)

An optional remote-LLM judge pass could re-read only the stories this validator
flags (status ``REVIEW``) and give a semantic verdict on truncation or bleed-over.
Not implemented, not required, and out of scope for this module — the validator is
intentionally local, deterministic, and dependency-free beyond PyMuPDF.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from .models import ExtractorConfig
from .normalizer import TextNormalizer
from .survey import EdgeCaseSurvey, FootnoteChain
from .toc import SectionRange, TableOfContentsParser

#: Below this many characters per PDF page a story is flagged ``LOW_DENSITY``.
MIN_CHARS_PER_PAGE = 800

DEFAULT_THRESHOLD = 0.90

#: Structural flags caused by an error printed in the textbook itself, keyed by
#: ``(story_number, flag)``. Story numbers are unique book-wide. A listed flag
#: is moved out of ``structural_flags`` into ``source_errata``: the story gets
#: status ``ERRATUM`` (reported separately, not ``REVIEW``). Only add an entry
#: after checking data.pdf confirms the source, not the extractor, is at fault.
KNOWN_SOURCE_ERRATA: Dict[Tuple[int, str], str] = {
    (52, "ORPHAN_MARKER:3"): (
        "textbook error: data.pdf page 357 prints footnote 3's number as '1', "
        "so its text (Theo Tạp chí chúng tôi (1910)) is merged into [^2]"
    ),
}


# ---------------------------------------------------------------------------
# Section A — core
# ---------------------------------------------------------------------------


@dataclass
class StoryValidationResult:
    """Per-story validation outcome."""

    story_number: int
    title: str
    markdown_file: str
    start_page: int
    end_page: int
    rendered_coverage: float
    raw_coverage: float
    char_per_page: float
    structural_flags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    threshold: float = DEFAULT_THRESHOLD
    #: Allow-listed flags (``FLAG — reason``) from :data:`KNOWN_SOURCE_ERRATA`.
    source_errata: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        """``REVIEW`` when below threshold or structurally flagged; ``ERRATUM``
        when the only issues are known textbook errors; else ``OK``."""
        if self.rendered_coverage < self.threshold or self.structural_flags:
            return "REVIEW"
        if self.source_errata:
            return "ERRATUM"
        return "OK"


def apply_source_errata(story_number: int, flags: List[str]) -> Tuple[List[str], List[str]]:
    """Split ``flags`` into ``(remaining_flags, errata)`` using :data:`KNOWN_SOURCE_ERRATA`."""
    remaining: List[str] = []
    errata: List[str] = []
    for flag in flags:
        reason = KNOWN_SOURCE_ERRATA.get((story_number, flag))
        if reason is None:
            remaining.append(flag)
        else:
            errata.append(f"{flag} — {reason}")
    return remaining, errata


def normalize_for_diff(text: str) -> str:
    """Normalize text for comparison without harming Vietnamese diacritics.

    Legacy-encoding repair -> Unicode NFC -> collapse whitespace runs -> strip.
    Never casefolds, strips diacritics, or ASCII-folds.
    """
    if not text:
        return ""
    text = TextNormalizer.normalize_encoding(text)
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
_HRULE_RE = re.compile(r"^\s*-{3,}\s*$")
_FOOTNOTE_DEF_RE = re.compile(r"^\[\^(\d+)\]:\s*(?:\(Trang\s*(\d+)\)\s*)?")
_INLINE_MARKER_RE = re.compile(r"\[\^(\d+)\]")
#: Blockquote marker of a rendered verse line (``> Cô hố cô hố.``).
_BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>\s?")
#: A footnote's continuation block (verse / prose after a verse) is indented.
_FOOTNOTE_CONT_RE = re.compile(r"^(?: {4}|\t)")
#: A paragraph that is only a dialogue dash — a dash orphaned from its speech.
_BARE_DASH_RE = re.compile(r"^[-–—]$")


def _unquote(line: str) -> str:
    """Drop a leading blockquote marker, keeping the verse text."""
    return _BLOCKQUOTE_RE.sub("", line)


def strip_markdown_scaffolding(md: str) -> str:
    """Drop Markdown scaffolding, leaving only prose that should exist in the PDF.

    Removes heading lines, the ``---`` rule, the ``### Chú thích`` label, the
    ``[^N]: (Trang N)`` footnote prefixes, the ``> `` verse blockquote markers
    (and a footnote continuation's indentation) and inline ``[^N]`` markers.
    Footnote *body* text and verse text are kept — they are real PDF text.
    """
    kept: List[str] = []
    for line in md.splitlines():
        if _HRULE_RE.match(line):
            continue
        if _HEADING_RE.match(line):
            # Headings (category, story title, KHẢO DỊ, Chú thích) are scaffolding.
            continue
        line = _unquote(line.strip())
        line = _FOOTNOTE_DEF_RE.sub("", line)
        line = _INLINE_MARKER_RE.sub("", line)
        if line.strip():
            kept.append(line)
    return "\n".join(kept)


def extract_raw_page_text(doc: "fitz.Document", start_page: int, end_page: int) -> str:
    """Deliberately dumb ground truth: joined ``page.get_text()`` over a 1-based
    inclusive page range, normalized for diff. No geometry filtering."""
    if start_page > end_page:
        return ""
    lo = max(1, start_page)
    hi = min(len(doc), end_page)
    chunks: List[str] = []
    for pno in range(lo - 1, hi):
        chunks.append(doc[pno].get_text())
    return normalize_for_diff("\n".join(chunks))


def score_alignment(raw: str, rendered: str) -> Tuple[float, float]:
    """Return ``(rendered_coverage, raw_coverage)``.

    ``autojunk=False`` is mandatory: the default heuristic silently discards
    frequent characters in strings longer than 200 chars and would corrupt every
    score on prose this long.
    """
    if not raw or not rendered:
        return (0.0, 0.0)
    matcher = difflib.SequenceMatcher(None, raw, rendered, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    rendered_coverage = matched / len(rendered) if rendered else 0.0
    raw_coverage = matched / len(raw) if raw else 0.0
    return (min(rendered_coverage, 1.0), min(raw_coverage, 1.0))


def split_rendered_segments(md: str) -> Tuple[str, List[Tuple[int, str]]]:
    """Split rendered Markdown into ``(body_text, [(page, footnote_text), ...])``.

    ``body_text`` is what :func:`strip_markdown_scaffolding` keeps **minus** the
    footnote-definition lines; those are returned separately, each carrying the
    page from its own ``(Trang P)`` prefix (``-1`` when missing/unparsable).
    A footnote's indented continuation lines (verse rendered inside a footnote)
    belong to that footnote. Verse ``> `` markers are stripped, text kept.
    """
    body_lines: List[str] = []
    fn_entries: List[List[Any]] = []
    in_footnote = False
    for line in md.splitlines():
        if in_footnote and (not line.strip() or _FOOTNOTE_CONT_RE.match(line)):
            text = _INLINE_MARKER_RE.sub("", _unquote(line.strip()))
            if text.strip():
                fn_entries[-1][1] = f"{fn_entries[-1][1]}\n{text}".strip()
            continue
        in_footnote = False
        if _HRULE_RE.match(line):
            continue
        if _HEADING_RE.match(line):
            continue
        stripped = line.strip()
        match = _FOOTNOTE_DEF_RE.match(stripped)
        if match:
            page = int(match.group(2)) if match.group(2) else -1
            text = _INLINE_MARKER_RE.sub("", _FOOTNOTE_DEF_RE.sub("", stripped))
            fn_entries.append([page, text])
            in_footnote = True
            continue
        line = _INLINE_MARKER_RE.sub("", _unquote(stripped))
        if line.strip():
            body_lines.append(line)
    return "\n".join(body_lines), [(page, text) for page, text in fn_entries if text.strip()]


def score_matched(raw: str, rendered: str) -> Tuple[int, int]:
    """Return ``(matched_chars, len(rendered))`` for one segment.

    Same ``SequenceMatcher(..., autojunk=False)`` call as :func:`score_alignment`;
    returns raw counts so segments can be combined length-weighted.
    """
    if not rendered:
        return (0, 0)
    if not raw:
        return (0, len(rendered))
    matcher = difflib.SequenceMatcher(None, raw, rendered, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return (min(matched, len(rendered)), len(rendered))


def score_segments(
    doc: "fitz.Document",
    start_page: int,
    end_page: int,
    body: str,
    fn_entries: List[Tuple[int, str]],
    rendered_full: str,
) -> Tuple[float, float]:
    """Return ``(rendered_coverage, raw_coverage)`` using segment-aware scoring.

    The body is scored against the story's full page range; each footnote is
    scored against its own ``(Trang P)`` page window (falling back to the full
    range when the page is missing or outside the story). Segment results are
    combined length-weighted. ``raw_coverage`` is the unchanged whole-blob value.

    Memory: the full-range raw text is loaded once per story and each per-page
    window is released immediately after use.
    """
    full_raw = extract_raw_page_text(doc, start_page, end_page)
    if not full_raw:
        return (0.0, 0.0)

    _, raw_cov = score_alignment(full_raw, rendered_full)

    total_matched = 0
    total_len = 0

    body_norm = normalize_for_diff(body)
    if body_norm:
        matched, length = score_matched(full_raw, body_norm)
        total_matched += matched
        total_len += length
    del body_norm

    for page, text in fn_entries:
        fn_norm = normalize_for_diff(text)
        if not fn_norm:
            continue
        if page == -1 or page < start_page or page > end_page:
            matched, length = score_matched(full_raw, fn_norm)
        else:
            window = extract_raw_page_text(doc, page, page)
            matched, length = score_matched(window, fn_norm)
            del window
        total_matched += matched
        total_len += length
        del fn_norm

    del full_raw
    rendered_cov = (total_matched / total_len) if total_len else 0.0
    return (min(rendered_cov, 1.0), raw_cov)


# ---------------------------------------------------------------------------
# Section B — structural checks
# ---------------------------------------------------------------------------


def parse_markdown_story(path: str) -> Dict[str, Any]:
    """Parse a rendered ``story_NNN.md`` into its structural parts.

    Returns ``{title, category, body, footnotes: List[Tuple[orig_num, page]],
    footnote_entries: List[Tuple[orig_num, page, text]], khao_di_present: bool}``.
    Missing/unreadable files yield empty structures rather than raising (the CLI
    is a reporting tool, never a crasher).

    ``footnotes`` stays ``(num, page)`` only — :func:`check_structure` depends on
    it; ``footnote_entries`` is the additive variant carrying the footnote text.
    """
    parsed: Dict[str, Any] = {
        "title": "",
        "category": "",
        "body": "",
        "footnotes": [],
        "footnote_entries": [],
        "khao_di_present": False,
        "read_error": "",
    }
    try:
        with open(path, "r", encoding="utf-8") as handle:
            md = handle.read()
    except OSError as exc:
        parsed["read_error"] = str(exc)
        return parsed

    body_lines: List[str] = []
    in_footnote = False
    for line in md.splitlines():
        stripped = line.strip()
        if in_footnote and (not stripped or _FOOTNOTE_CONT_RE.match(line)):
            text = _INLINE_MARKER_RE.sub("", _unquote(stripped))
            if text:
                num, page, prev = parsed["footnote_entries"][-1]
                parsed["footnote_entries"][-1] = (num, page, f"{prev}\n{text}".strip())
            continue
        in_footnote = False
        if stripped.upper().startswith("### KHẢO DỊ"):
            parsed["khao_di_present"] = True
            continue
        if stripped.startswith("### "):
            continue
        if stripped.startswith("## ") and not parsed["title"]:
            title = stripped[3:].strip()
            title = re.sub(r"^\d+\.\s*", "", title)
            parsed["title"] = title
            continue
        if stripped.startswith("# ") and not parsed["category"]:
            parsed["category"] = stripped[2:].strip()
            continue
        match = _FOOTNOTE_DEF_RE.match(stripped)
        if match:
            page = int(match.group(2)) if match.group(2) else -1
            num = int(match.group(1))
            parsed["footnotes"].append((num, page))
            parsed["footnote_entries"].append(
                (num, page, _INLINE_MARKER_RE.sub("", _FOOTNOTE_DEF_RE.sub("", stripped)))
            )
            in_footnote = True
            continue
        if _HRULE_RE.match(line) or stripped.startswith("#"):
            continue
        stripped = _unquote(stripped)
        if stripped:
            body_lines.append(stripped)

    parsed["body"] = "\n".join(body_lines)
    parsed["raw_markdown"] = md
    return parsed


def check_structure(md_parsed: Dict[str, Any], toc_entry: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Return ``(flags, notes)`` for one story's structural integrity."""
    flags: List[str] = []
    notes: List[str] = []

    if md_parsed.get("read_error"):
        flags.append("UNREADABLE_FILE")
        return flags, notes

    if not md_parsed.get("title"):
        flags.append("EMPTY_TITLE")
    if not md_parsed.get("category"):
        flags.append("EMPTY_CATEGORY")
    if not md_parsed.get("body", "").strip():
        flags.append("EMPTY_BODY")

    footnotes: List[Tuple[int, int]] = md_parsed.get("footnotes", [])
    footnote_nums = [num for num, _ in footnotes]
    body_markers = [int(n) for n in _INLINE_MARKER_RE.findall(md_parsed.get("body", ""))]

    for num in sorted(set(body_markers)):
        if num not in footnote_nums:
            flags.append(f"ORPHAN_MARKER:{num}")
    for num in sorted(set(footnote_nums)):
        if num not in body_markers:
            flags.append(f"ORPHAN_FOOTNOTE:{num}")

    # A dash alone on its own paragraph is a dialogue dash orphaned from its
    # speech (the page-boundary dialogue bug) — regression guard.
    if any(_BARE_DASH_RE.match(line.strip()) for line in md_parsed.get("body", "").splitlines()):
        flags.append("BARE_DASH_PARAGRAPH")

    # A number's pages must stay inside the story and in page order; with
    # per-page renumbering a skipped page is fine, going backwards is not.
    start, end = toc_entry.get("start_page"), toc_entry.get("end_page")
    pages_by_num: Dict[int, List[int]] = {}
    for num, page in footnotes:
        pages_by_num.setdefault(num, []).append(page)
    for num, pages in sorted(pages_by_num.items()):
        out_of_range = start is not None and end is not None and any(
            p != -1 and not (int(start) <= p <= int(end)) for p in pages
        )
        if out_of_range or pages != sorted(pages):
            flags.append(f"FOOTNOTE_GAP:{num}")

    # Per-page footnote renumbering is expected: a duplicate number across
    # different pages is a note, never a failure.
    seen: Dict[int, List[int]] = {}
    for num, page in footnotes:
        seen.setdefault(num, []).append(page)
    for num, pages in sorted(seen.items()):
        if len(pages) > 1:
            if len(set(pages)) > 1:
                notes.append(
                    f"footnote [^{num}] appears {len(pages)}x on pages {sorted(set(pages))} "
                    f"(per-page renumbering, expected)"
                )
            else:
                notes.append(f"footnote [^{num}] defined {len(pages)}x on the same page {pages[0]}")

    if toc_entry.get("footnote_count") is not None and len(footnotes) != toc_entry["footnote_count"]:
        notes.append(
            f"TOC footnote_count={toc_entry['footnote_count']} but markdown has {len(footnotes)}"
        )

    return flags, notes


def check_footnote_chains(
    footnotes: List[Tuple[int, int]],
    chains: List[FootnoteChain],
    start_page: int,
    end_page: int,
) -> List[str]:
    """Flag ``FOOTNOTE_GAP:N`` when a footnote continued over a page break is
    missing a link in the rendered Markdown.

    ``chains`` come from the raw PDF footer (:meth:`EdgeCaseSurvey.find_footnote_chains`):
    footnote ``N`` spread over consecutive pages. Every chain page inside the
    story must carry an ``[^N]: (Trang P)`` entry — a continuation that was
    dropped or lost its number (rendered as some other ``[^M]``) breaks the chain.
    """
    present = set(footnotes)
    flags: List[str] = []
    for chain in chains:
        pages = [p for p in chain.pages if start_page <= p <= end_page]
        if any((chain.num, p) not in present for p in pages):
            flag = f"FOOTNOTE_GAP:{chain.num}"
            if flag not in flags:
                flags.append(flag)
    return flags


def check_completeness(
    doc: "fitz.Document",
    section: Optional[SectionRange],
    story_numbers: List[int],
) -> List[str]:
    """Section-level story-count check against the printed MỤC LỤC."""
    flags: List[str] = []
    if section is None:
        return flags
    try:
        entries = TableOfContentsParser.parse_entries(doc)
    except Exception as exc:  # reporting tool — never crash on a TOC quirk
        return [f"TOC_UNREADABLE: {exc}"]

    expected = [
        e for e in entries
        if TableOfContentsParser.STORY_PAT.match(e.title)
        and section.start_page <= e.page <= section.end_page
    ]
    delta = len(story_numbers) - len(expected)
    if delta < 0:
        flags.append(
            f"MISSING_STORIES: TOC lists {len(expected)} in pages "
            f"{section.start_page}-{section.end_page}, extracted {len(story_numbers)} (delta {delta})"
        )
    elif delta > 0:
        flags.append(
            f"EXTRA_STORIES: TOC lists {len(expected)} in pages "
            f"{section.start_page}-{section.end_page}, extracted {len(story_numbers)} (delta +{delta})"
        )
    return flags


# ---------------------------------------------------------------------------
# Section C — orchestration
# ---------------------------------------------------------------------------


class ExtractionValidator:
    """Validates a section's on-disk extraction output against the source PDF."""

    @staticmethod
    def _load_toc(input_dir: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        toc_path = os.path.join(input_dir, "table_of_contents.json")
        if not os.path.exists(toc_path):
            return [], [f"MISSING_TOC: {toc_path} not found — nothing to validate"]
        try:
            with open(toc_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return [], [f"UNREADABLE_TOC: {toc_path} ({exc})"]

        stories: List[Dict[str, Any]] = []
        for section in data.get("sections", []):
            for story in section.get("stories", []):
                stories.append(story)
        if not stories:
            return [], [f"EMPTY_TOC: no stories listed in {toc_path}"]
        return stories, []

    @classmethod
    def validate_section(
        cls,
        pdf_path: str,
        input_dir: str,
        threshold: float = DEFAULT_THRESHOLD,
        section: Optional[SectionRange] = None,
    ) -> Tuple[List[StoryValidationResult], List[str]]:
        """Validate every story in ``input_dir``. Returns ``(results, section_flags)``.

        One story's text is held in memory at a time; nothing is accumulated.
        """
        results: List[StoryValidationResult] = []
        stories, section_flags = cls._load_toc(input_dir)
        if not stories:
            return results, section_flags

        if not os.path.exists(pdf_path):
            section_flags.append(f"MISSING_PDF: {pdf_path} not found — alignment scoring skipped")
            doc = None
        else:
            doc = fitz.open(pdf_path)

        try:
            if doc is not None:
                section_flags.extend(
                    check_completeness(doc, section, [s.get("story_number", -1) for s in stories])
                )

            for story in stories:
                number = int(story.get("story_number", -1))
                md_name = story.get("markdown_file") or f"story_{number:03d}.md"
                md_path = os.path.join(input_dir, md_name)
                start_page = int(story.get("start_page", 0) or 0)
                end_page = int(story.get("end_page", 0) or 0)

                parsed = parse_markdown_story(md_path)
                flags, notes = check_structure(parsed, story)
                if doc is not None and not parsed.get("read_error"):
                    chains = EdgeCaseSurvey.find_footnote_chains(
                        doc, start_page, end_page, ExtractorConfig()
                    )
                    for flag in check_footnote_chains(
                        parsed.get("footnotes", []), chains, start_page, end_page
                    ):
                        if flag not in flags:
                            flags.append(flag)

                rendered = normalize_for_diff(
                    strip_markdown_scaffolding(parsed.get("raw_markdown", ""))
                )
                page_span = max(1, end_page - start_page + 1)
                char_per_page = len(rendered) / page_span

                if char_per_page < MIN_CHARS_PER_PAGE:
                    flags.append("LOW_DENSITY")
                flags, errata = apply_source_errata(number, flags)

                if doc is not None and rendered:
                    body_seg, fn_segs = split_rendered_segments(
                        parsed.get("raw_markdown", "")
                    )
                    rendered_cov, raw_cov = score_segments(
                        doc, start_page, end_page, body_seg, fn_segs, rendered
                    )
                    del body_seg, fn_segs
                else:
                    rendered_cov, raw_cov = 0.0, 0.0

                results.append(
                    StoryValidationResult(
                        story_number=number,
                        title=story.get("title", "") or parsed.get("title", ""),
                        markdown_file=md_name,
                        start_page=start_page,
                        end_page=end_page,
                        rendered_coverage=rendered_cov,
                        raw_coverage=raw_cov,
                        char_per_page=char_per_page,
                        structural_flags=flags,
                        notes=notes,
                        threshold=threshold,
                        source_errata=errata,
                    )
                )
                del parsed, rendered
        finally:
            if doc is not None:
                doc.close()

        return results, section_flags


class ValidationReporter:
    """Renders validation results worst-first."""

    @staticmethod
    def _sorted(results: List[StoryValidationResult]) -> List[StoryValidationResult]:
        # rendered_coverage is the ONLY sort key; raw_coverage is informational.
        return sorted(results, key=lambda r: (r.rendered_coverage, r.story_number))

    @classmethod
    def render_markdown(
        cls,
        results: List[StoryValidationResult],
        section_flags: List[str],
        threshold: float = DEFAULT_THRESHOLD,
    ) -> str:
        ordered = cls._sorted(results)
        review = [r for r in ordered if r.status == "REVIEW"]
        flagged = [r for r in ordered if r.structural_flags]
        errata = [r for r in ordered if r.source_errata]

        lines: List[str] = []
        lines.append("# Extraction Validation Report")
        lines.append("")
        lines.append(f"- Stories validated: **{len(results)}**")
        lines.append(f"- Threshold (rendered_coverage): **{threshold:.2f}**")
        lines.append(f"- Needing review: **{len(review)}**")
        lines.append(f"- With structural flags: **{len(flagged)}**")
        lines.append(f"- Known source errata: **{len(errata)}**")
        lines.append("")
        lines.append(
            "`rendered_coverage` = fraction of the rendered Markdown prose found in the raw PDF "
            "page text (primary metric, sort key, threshold). `raw_coverage` is **informational "
            "only** — adjacent stories share boundary pages, so it is expected to be noisy."
        )
        lines.append("")

        lines.append("## Section-level checks")
        lines.append("")
        if section_flags:
            for flag in section_flags:
                lines.append(f"- {flag}")
        else:
            lines.append("- No section-level issues.")
        lines.append("")

        lines.append("## Stories (worst first)")
        lines.append("")
        lines.append("| # | Story | Pages | rendered_cov | raw_cov (info) | chars/page | Status | Flags |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in ordered:
            shown = r.structural_flags + [f"ERRATUM: {e.split(' — ')[0]}" for e in r.source_errata]
            flags = ", ".join(shown) if shown else "-"
            lines.append(
                f"| {r.story_number} | {r.title} | {r.start_page}-{r.end_page} | "
                f"{r.rendered_coverage:.3f} | {r.raw_coverage:.3f} | {r.char_per_page:.0f} | "
                f"{r.status} | {flags} |"
            )
        lines.append("")

        lines.append("## Structural Failures")
        lines.append("")
        if flagged:
            for r in flagged:
                lines.append(f"### Story {r.story_number} — {r.title} (`{r.markdown_file}`)")
                for flag in r.structural_flags:
                    lines.append(f"- FLAG: {flag}")
                lines.append("")
        else:
            lines.append("- None.")
        lines.append("")

        lines.append("## Known Source Errata")
        lines.append("")
        lines.append(
            "Flags caused by an error printed in the textbook itself (allow-listed in "
            "`KNOWN_SOURCE_ERRATA`); these stories are not counted as needing review."
        )
        lines.append("")
        if errata:
            for r in errata:
                lines.append(f"### Story {r.story_number} — {r.title} (`{r.markdown_file}`)")
                for entry in r.source_errata:
                    lines.append(f"- ERRATUM: {entry}")
                lines.append("")
        else:
            lines.append("- None.")
        lines.append("")

        noted = [r for r in ordered if r.notes]
        lines.append("## Notes (informational)")
        lines.append("")
        if noted:
            for r in noted:
                lines.append(f"- Story {r.story_number}: " + "; ".join(r.notes))
        else:
            lines.append("- None.")
        lines.append("")
        return "\n".join(lines)

    @classmethod
    def render_console(
        cls,
        results: List[StoryValidationResult],
        section_flags: List[str],
        top_n: int = 15,
    ) -> str:
        ordered = cls._sorted(results)
        review = [r for r in ordered if r.status == "REVIEW"]
        lines: List[str] = []
        lines.append(
            f"Validated {len(results)} stories — {len(review)} need review, "
            f"{len([r for r in ordered if r.structural_flags])} with structural flags, "
            f"{len([r for r in ordered if r.source_errata])} known source errata."
        )
        for flag in section_flags:
            lines.append(f"  [section] {flag}")
        if not ordered:
            lines.append("  (no stories found)")
            return "\n".join(lines)

        lines.append(f"Worst {min(top_n, len(ordered))} by rendered_coverage:")
        lines.append(f"  {'#':>4}  {'rend':>6}  {'raw*':>6}  {'c/pg':>6}  status  title / flags")
        for r in ordered[:top_n]:
            shown = r.structural_flags + [f"ERRATUM: {e.split(' — ')[0]}" for e in r.source_errata]
            flags = (" | " + ", ".join(shown)) if shown else ""
            lines.append(
                f"  {r.story_number:>4}  {r.rendered_coverage:>6.3f}  {r.raw_coverage:>6.3f}  "
                f"{r.char_per_page:>6.0f}  {r.status:<6}  {r.title}{flags}"
            )
        lines.append("  (* raw_coverage informational only — noisy on shared boundary pages)")
        return "\n".join(lines)
