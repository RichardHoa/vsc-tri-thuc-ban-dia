"""
Extraction Accuracy Validator.

Read-only quality checks over already-extracted output. Never mutates
extraction results: it reads each leaf (Story, Essay, Introduction) back — via
the Section folders' `table_of_contents.json` and each Part's
`introduction.md` — re-reads the raw PyMuPDF page text for the leaf's page
range, and scores text fidelity with `difflib`.

Two kinds of signal are produced:

* **Structural checks** — empty title/category/body, orphan footnote markers and
  orphan footnote entries matched on (page, number), bare ``-`` paragraphs,
  footnote-chain gaps, low character density, Section-level Story/Essay count
  drift against MỤC LỤC.
* **Text alignment** — `rendered_coverage` (what fraction of the rendered Markdown
  prose is found in the raw PDF page text) is the primary metric and the report's
  sort key / threshold. It is scored **per segment**: the body prose is diffed
  against the leaf's full page range, and each footnote body is diffed against a
  window anchored to its own ``(Trang P)`` page, then the segments are combined
  length-weighted. This is required because ``MarkdownRenderer`` relocates every
  footnote body to an end-of-file block while the raw PDF keeps them interleaved
  per page; a whole-blob ``difflib`` diff is defeated by that reordering and
  reports false-low scores on footnote-heavy leaves. The body diff also places
  each body marker on its page for the orphan checks. `raw_coverage` is
  **informational only**: adjacent leaves share PDF boundary pages, so a leaf's
  page range legitimately contains a neighbour's text and raw coverage is
  inherently noisy. It must never be used to fail or sort a leaf.

Memory is deliberately bounded: each worker process holds exactly one leaf's raw +
rendered text at a time, never a whole-Section blob (`difflib.SequenceMatcher` is
quadratic-ish).

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
from bisect import bisect_right
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import fitz  # PyMuPDF

from .models import ExtractorConfig
from .normalizer import TextNormalizer
from .pipeline import BookPipeline
from .survey import EdgeCaseSurvey, FootnoteChain
from .toc import PartRange, SectionRange, TableOfContentsParser

#: Below this many characters per PDF page a story is flagged ``LOW_DENSITY``.
MIN_CHARS_PER_PAGE = 800

DEFAULT_THRESHOLD = 0.90

#: Structural flags caused by an error printed in the textbook itself, keyed by
#: ``(errata_key, flag)``: a Story's number (unique book-wide), else the leaf's
#: label (``"Essay V.2"``, ``"Introduction PHAN_THU_BA"``). A listed flag
#: is moved out of ``structural_flags`` into ``source_errata``: the story gets
#: status ``ERRATUM`` (reported separately, not ``REVIEW``). Only add an entry
#: after checking data.pdf confirms the source, not the extractor, is at fault.
KNOWN_SOURCE_ERRATA: Dict[Tuple[Union[int, str], str], str] = {
    (97, "EMPTY_FOOTNOTE:1"): (
        "textbook error: data.pdf page 601 prints footnote 1's number with no "
        "footnote text after it"
    ),
    (108, "ORPHAN_MARKER:2@657"): (
        "textbook error: data.pdf page 657 prints both of its footnotes as '1.', "
        "so footnote 2's text (Theo Đơ-jor-jơ (Degeorge) ...) is merged into [^1]"
    ),
    (52, "ORPHAN_MARKER:3@357"): (
        "textbook error: data.pdf page 357 prints footnote 3's number as '1', "
        "so its text (Theo Tạp chí chúng tôi (1910)) is merged into [^2]"
    ),
}


#: Section-level count drift caused by MỤC LỤC itself, keyed by
#: ``(section path, flag code, delta)``. Reported as an erratum, not a flag.
KNOWN_TOC_ERRATA: Dict[Tuple[str, str, int], str] = {
    ("PHAN_THU_BA/V_THU_TIM_NGUON_GOC_TRUYEN_CO_TICH_VIET_NAM", "EXTRA_ESSAYS", 1): (
        "MỤC LỤC omits Essay 1 (CÁC TRƯỜNG PHÁI CỔ TÍCH HỌC XƯA NAY..., p. 1392, set "
        "non-bold); the printed text is the authority, so it is extracted"
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
    #: ``story`` | ``essay`` | ``introduction``.
    kind: str = "story"
    #: Display name (``Essay V.2``, ``Introduction``); a Story's is derived.
    label: str = ""
    #: Part and Section titles, for grouping the report ("" for an Introduction's Section).
    part: str = ""
    section: str = ""

    @property
    def display_label(self) -> str:
        return self.label or f"Story {self.story_number}"

    @property
    def status(self) -> str:
        """``REVIEW`` when below threshold or structurally flagged; ``ERRATUM``
        when the only issues are known textbook errors; else ``OK``."""
        if self.rendered_coverage < self.threshold or self.structural_flags:
            return "REVIEW"
        if self.source_errata:
            return "ERRATUM"
        return "OK"


def apply_source_errata(errata_key: Union[int, str], flags: List[str]) -> Tuple[List[str], List[str]]:
    """Split ``flags`` into ``(remaining_flags, errata)`` using :data:`KNOWN_SOURCE_ERRATA`."""
    remaining: List[str] = []
    errata: List[str] = []
    for flag in flags:
        reason = KNOWN_SOURCE_ERRATA.get((errata_key, flag))
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
#: ``[^N]: (Trang P)`` or, for a footnote merged over a page break, ``(Trang P-Q)``.
_FOOTNOTE_DEF_RE = re.compile(r"^\[\^(\d+)\]:\s*(?:\(Trang\s*(\d+)(?:\s*[-–]\s*(\d+))?\)\s*)?")


def _def_pages(match: "re.Match") -> Tuple[int, int]:
    """``(start, end)`` pages of a footnote definition (``(-1, -1)`` if missing)."""
    if not match.group(2):
        return (-1, -1)
    start = int(match.group(2))
    return (start, int(match.group(3)) if match.group(3) else start)
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
    return extract_raw_pages(doc, start_page, end_page)[0]


def extract_raw_pages(
    doc: "fitz.Document", start_page: int, end_page: int
) -> Tuple[str, List[Tuple[int, int]]]:
    """:func:`extract_raw_page_text` plus ``(offset, page)`` where each page starts in it.

    Each page is normalized on its own and joined with one space — the same
    text as normalizing the joined pages, since whitespace runs collapse.
    """
    starts: List[Tuple[int, int]] = []
    chunks: List[str] = []
    offset = 0
    for pno in range(max(1, start_page) - 1, min(len(doc), end_page)):
        text = normalize_for_diff(doc[pno].get_text())
        if not text:
            continue
        if chunks:
            offset += 1
        starts.append((offset, pno + 1))
        chunks.append(text)
        offset += len(text)
    return " ".join(chunks), starts


def strip_markers(text: str) -> Tuple[str, List[Tuple[int, int]]]:
    """``normalize_for_diff`` of ``text`` without its ``[^N]`` markers, plus
    ``(offset, N)`` per marker: where it stood in that stripped text."""
    text = normalize_for_diff(text)
    out = ""
    offsets: List[Tuple[int, int]] = []
    pos = 0
    for m in _INLINE_MARKER_RE.finditer(text):
        out += text[pos:m.start()]
        offsets.append((len(out), int(m.group(1))))
        pos = m.end()
        if out.endswith(" ") and text[pos:pos + 1] == " ":
            pos += 1  # "SINH [^1] x": the spaces either side collapse to one
    out += text[pos:]
    lead = len(out) - len(out.lstrip())
    out = out.strip()
    return out, [(min(max(o - lead, 0), len(out)), n) for o, n in offsets]


def marker_pages(
    blocks: List["difflib.Match"],
    offsets: List[Tuple[int, int]],
    page_starts: List[Tuple[int, int]],
) -> List[Tuple[Optional[int], int]]:
    """``(page, N)`` per body marker, from the body ↔ raw ``SequenceMatcher`` blocks.

    A marker is on the page of the character it follows. When that character
    is unmatched, the nearest matched one before it is used, and the first
    page when there is none. ``None`` only without raw text.
    """
    if not page_starts:
        return [(None, n) for _, n in offsets]
    bounds = [o for o, _ in page_starts]
    out: List[Tuple[Optional[int], int]] = []
    for offset, num in offsets:
        char = max(offset - 1, 0)
        raw_pos = None
        for a, b, size in blocks:
            if b > char or not size:
                break
            raw_pos = a + min(char - b, size - 1)
        idx = bisect_right(bounds, raw_pos) - 1 if raw_pos is not None else 0
        out.append((page_starts[idx][1], num))
    return out


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


def split_rendered_segments(
    md: str, keep_markers: bool = False
) -> Tuple[str, List[Tuple[int, int, str]]]:
    """Split rendered Markdown into ``(body_text, [(page, end_page, footnote_text), ...])``.

    ``body_text`` is what :func:`strip_markdown_scaffolding` keeps **minus** the
    footnote-definition lines (with its ``[^N]`` markers when ``keep_markers``);
    those are returned separately, each carrying the
    pages from its own ``(Trang P)`` / ``(Trang P-Q)`` prefix (``-1`` when
    missing/unparsable).
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
                fn_entries[-1][2] = f"{fn_entries[-1][2]}\n{text}".strip()
            continue
        in_footnote = False
        if _HRULE_RE.match(line):
            continue
        if _HEADING_RE.match(line):
            continue
        stripped = line.strip()
        match = _FOOTNOTE_DEF_RE.match(stripped)
        if match:
            page, last = _def_pages(match)
            text = _INLINE_MARKER_RE.sub("", _FOOTNOTE_DEF_RE.sub("", stripped))
            fn_entries.append([page, last, text])
            in_footnote = True
            continue
        line = _unquote(stripped)
        if not keep_markers:
            line = _INLINE_MARKER_RE.sub("", line)
        if line.strip():
            body_lines.append(line)
    return "\n".join(body_lines), [(p, e, text) for p, e, text in fn_entries if text.strip()]


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
    fn_entries: List[Tuple[int, int, str]],
    rendered_full: str,
) -> Tuple[float, float, List[Tuple[Optional[int], int]]]:
    """Return ``(rendered_coverage, raw_coverage, body_marker_pages)`` using
    segment-aware scoring.

    The body (``[^N]`` markers allowed) is scored against the story's full page
    range, and that alignment places each body marker on its page (see
    :func:`marker_pages`); each footnote is
    scored against its own ``(Trang P)`` page window (falling back to the full
    range when the page is missing or outside the story). Segment results are
    combined length-weighted. ``raw_coverage`` is the unchanged whole-blob value.

    Memory: the full-range raw text is loaded once per story and each per-page
    window is released immediately after use.
    """
    full_raw, page_starts = extract_raw_pages(doc, start_page, end_page)
    body_norm, offsets = strip_markers(body)
    if not full_raw:
        return (0.0, 0.0, [(None, n) for _, n in offsets])

    _, raw_cov = score_alignment(full_raw, rendered_full)

    total_matched = 0
    total_len = 0
    markers: List[Tuple[Optional[int], int]] = [(None, n) for _, n in offsets]

    if body_norm:
        matcher = difflib.SequenceMatcher(None, full_raw, body_norm, autojunk=False)
        blocks = matcher.get_matching_blocks()
        total_matched += min(sum(block.size for block in blocks), len(body_norm))
        total_len += len(body_norm)
        markers = marker_pages(blocks, offsets, page_starts)
        del matcher, blocks
    del body_norm

    for page, last, text in fn_entries:
        fn_norm = normalize_for_diff(text)
        if not fn_norm:
            continue
        if page == -1 or page < start_page or last > end_page:
            matched, length = score_matched(full_raw, fn_norm)
        else:
            window = extract_raw_page_text(doc, page, last)
            matched, length = score_matched(window, fn_norm)
            del window
        total_matched += matched
        total_len += length
        del fn_norm

    del full_raw
    rendered_cov = (total_matched / total_len) if total_len else 0.0
    return (min(rendered_cov, 1.0), raw_cov, markers)


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
        "footnote_ranges": [],
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
            page, last = _def_pages(match)
            num = int(match.group(1))
            parsed["footnotes"].append((num, page))
            parsed["footnote_ranges"].append((num, page, last))
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


def check_structure(
    md_parsed: Dict[str, Any], toc_entry: Dict[str, Any], require_title: bool = True
) -> Tuple[List[str], List[str]]:
    """Return ``(flags, notes)`` for one leaf's structural integrity.

    Orphan markers / footnotes are checked separately (:func:`check_orphans`):
    they need each marker's page. An Introduction has no title
    (``require_title=False``).
    """
    flags: List[str] = []
    notes: List[str] = []

    if md_parsed.get("read_error"):
        flags.append("UNREADABLE_FILE")
        return flags, notes

    if require_title and not md_parsed.get("title"):
        flags.append("EMPTY_TITLE")
    if not md_parsed.get("category"):
        flags.append("EMPTY_CATEGORY")
    if not md_parsed.get("body", "").strip():
        flags.append("EMPTY_BODY")

    footnotes: List[Tuple[int, int]] = md_parsed.get("footnotes", [])

    # A footnote definition with no text at all.
    for num, _, text in md_parsed.get("footnote_entries", []):
        if not text.strip():
            flag = f"EMPTY_FOOTNOTE:{num}"
            if flag not in flags:
                flags.append(flag)

    # A dash alone on its own paragraph is a dialogue dash orphaned from its
    # speech (the page-boundary dialogue bug) — regression guard.
    if any(_BARE_DASH_RE.match(line.strip()) for line in md_parsed.get("body", "").splitlines()):
        flags.append("BARE_DASH_PARAGRAPH")

    # A number's pages must stay inside the story and in page order; with
    # per-page renumbering a skipped page is fine, going backwards is not.
    start, end = toc_entry.get("start_page"), toc_entry.get("end_page")
    ranges = md_parsed.get("footnote_ranges") or [(n, p, p) for n, p in footnotes]
    pages_by_num: Dict[int, List[int]] = {}
    for num, page, _ in ranges:
        pages_by_num.setdefault(num, []).append(page)
    last_by_num: Dict[int, List[int]] = {}
    for num, _, last in ranges:
        last_by_num.setdefault(num, []).append(last)
    for num, pages in sorted(pages_by_num.items()):
        out_of_range = start is not None and end is not None and any(
            p != -1 and not (int(start) <= p <= int(end))
            for p in pages + last_by_num[num]
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


def check_orphans(
    markers: List[Tuple[Optional[int], int]],
    footnotes: List[Tuple[int, int, int]],
) -> List[str]:
    """``ORPHAN_MARKER:N@P`` / ``ORPHAN_FOOTNOTE:N@P``, matching on (page, number).

    Footnote numbers restart on every page, so a marker matches only the
    definition of its own number on its own page — a same-numbered marker
    elsewhere must not hide a missing one. ``markers`` are ``(page, N)`` in
    reading order (``page`` ``None`` when it could not be located: matched by
    number alone); ``footnotes`` are ``(N, page, end_page)``, matched on their
    first page (by number alone when it has no ``(Trang P)``, page ``-1``).
    """
    defined = {(page, num) for num, page, _ in footnotes}
    defined_nums = {num for num, _, _ in footnotes}
    unpaged = {num for num, page, _ in footnotes if page == -1}
    located = {(page, num) for page, num in markers if page is not None}
    marker_nums = {num for _, num in markers}
    unlocated = {num for page, num in markers if page is None}

    flags: List[str] = []
    for page, num in markers:
        if page is None:
            flag = None if num in defined_nums else f"ORPHAN_MARKER:{num}"
        else:
            flag = None if (page, num) in defined or num in unpaged else f"ORPHAN_MARKER:{num}@{page}"
        if flag and flag not in flags:
            flags.append(flag)
    for num, page, _ in footnotes:
        if (page, num) in located or num in unlocated or (page == -1 and num in marker_nums):
            continue
        flag = f"ORPHAN_FOOTNOTE:{num}@{page}"
        if flag not in flags:
            flags.append(flag)
    return flags


def heading_markers(md: str) -> List[int]:
    """Footnote numbers printed in the ``#`` / ``##`` headings (Part, Section,
    Story or Essay title), which sit on the leaf's first page."""
    return [
        int(n)
        for line in md.splitlines()
        if re.match(r"^#{1,2}\s", line)
        for n in _INLINE_MARKER_RE.findall(line)
    ]


def check_footnote_chains(
    footnotes: List[Tuple[int, ...]],
    chains: List[FootnoteChain],
    start_page: int,
    end_page: int,
) -> List[str]:
    """Flag ``FOOTNOTE_GAP:N`` when a footnote continued over a page break is
    missing a link in the rendered Markdown.

    ``chains`` come from the raw PDF footer (:meth:`EdgeCaseSurvey.find_footnote_chains`):
    footnote ``N`` spread over consecutive pages. Every chain page inside the
    story must be covered by an ``[^N]`` entry — ``(Trang P-Q)`` when merged,
    or ``(Trang P)`` — a continuation that was dropped or lost its number
    (rendered as some other ``[^M]``) breaks the chain. ``footnotes`` holds
    ``(num, page)`` or ``(num, page, end_page)`` tuples.
    """
    covered = set()
    for entry in footnotes:
        num, page = entry[0], entry[1]
        last = entry[2] if len(entry) > 2 else page
        covered.update((num, p) for p in range(page, last + 1))
    flags: List[str] = []
    for chain in chains:
        pages = [p for p in chain.pages if start_page <= p <= end_page]
        if any((chain.num, p) not in covered for p in pages):
            flag = f"FOOTNOTE_GAP:{chain.num}"
            if flag not in flags:
                flags.append(flag)
    return flags


def check_completeness(
    doc: "fitz.Document",
    section: Optional[SectionRange],
    leaf_numbers: List[int],
    leaf_kind: str = "stories",
) -> Tuple[List[str], List[str]]:
    """Section-level leaf-count check against the printed MỤC LỤC.

    Returns ``(flags, errata)``: a drift listed in :data:`KNOWN_TOC_ERRATA` is
    an erratum (``FLAG — reason``), not a flag.
    """
    if section is None:
        return [], []
    try:
        entries = TableOfContentsParser.parse_entries(doc)
    except Exception as exc:  # reporting tool — never crash on a TOC quirk
        return [f"TOC_UNREADABLE: {exc}"], []

    expected = [
        e for e in entries
        if TableOfContentsParser.STORY_PAT.match(e.title)
        and section.start_page <= e.page <= section.end_page
    ]
    delta = len(leaf_numbers) - len(expected)
    if delta == 0:
        return [], []
    code = f"{'MISSING' if delta < 0 else 'EXTRA'}_{leaf_kind.upper()}"
    flag = (
        f"{code}: TOC lists {len(expected)} in pages {section.start_page}-{section.end_page}, "
        f"extracted {len(leaf_numbers)} (delta {delta:+d})"
    )
    reason = KNOWN_TOC_ERRATA.get((section.path, code, delta))
    if reason is not None:
        return [], [f"{flag} — {reason}"]
    return [flag], []


# ---------------------------------------------------------------------------
# Section C — orchestration
# ---------------------------------------------------------------------------


@dataclass
class LeafJob:
    """One leaf (Story, Essay or Introduction) to validate."""

    kind: str
    number: int
    title: str
    label: str
    md_path: str
    start_page: int
    end_page: int
    toc_entry: Dict[str, Any]
    #: Key into :data:`KNOWN_SOURCE_ERRATA`.
    errata_key: Union[int, str]
    part: str = ""
    section: str = ""


def validate_leaf(
    doc: Optional["fitz.Document"], job: LeafJob, threshold: float = DEFAULT_THRESHOLD
) -> StoryValidationResult:
    """Structural checks and alignment scores for one leaf (``doc`` ``None``: no PDF)."""
    parsed = parse_markdown_story(job.md_path)
    md = parsed.get("raw_markdown", "")
    flags, notes = check_structure(parsed, job.toc_entry, require_title=job.kind != "introduction")
    if doc is not None and not parsed.get("read_error"):
        chains = EdgeCaseSurvey.find_footnote_chains(
            doc, job.start_page, job.end_page, ExtractorConfig()
        )
        for flag in check_footnote_chains(
            parsed.get("footnote_ranges", []), chains, job.start_page, job.end_page
        ):
            if flag not in flags:
                flags.append(flag)

    rendered = normalize_for_diff(strip_markdown_scaffolding(md))
    char_per_page = len(rendered) / max(1, job.end_page - job.start_page + 1)
    if char_per_page < MIN_CHARS_PER_PAGE:
        flags.append("LOW_DENSITY")

    if doc is not None and rendered:
        body_seg, fn_segs = split_rendered_segments(md, keep_markers=True)
        rendered_cov, raw_cov, body_markers = score_segments(
            doc, job.start_page, job.end_page, body_seg, fn_segs, rendered
        )
        del body_seg, fn_segs
    else:
        rendered_cov, raw_cov = 0.0, 0.0
        body_markers = [(None, int(n)) for n in _INLINE_MARKER_RE.findall(parsed.get("body", ""))]

    if not parsed.get("read_error"):
        markers = [(job.start_page, n) for n in heading_markers(md)] + body_markers
        flags.extend(check_orphans(markers, parsed.get("footnote_ranges", [])))
    flags, errata = apply_source_errata(job.errata_key, flags)

    return StoryValidationResult(
        story_number=job.number,
        title=job.title or parsed.get("title", ""),
        markdown_file=os.path.basename(job.md_path),
        start_page=job.start_page,
        end_page=job.end_page,
        rendered_coverage=rendered_cov,
        raw_coverage=raw_cov,
        char_per_page=char_per_page,
        structural_flags=flags,
        notes=notes,
        threshold=threshold,
        source_errata=errata,
        kind=job.kind,
        label=job.label,
        part=job.part,
        section=job.section,
    )


#: The PDF each worker process opens once (``fitz.Document`` can't be pickled).
_worker_doc: Optional["fitz.Document"] = None


def _open_worker_doc(pdf_path: str) -> None:
    global _worker_doc
    _worker_doc = fitz.open(pdf_path)


def _validate_in_worker(args: Tuple[LeafJob, float]) -> StoryValidationResult:
    return _validate_reported(_worker_doc, *args)


def _validate_reported(
    doc: Optional["fitz.Document"], job: LeafJob, threshold: float
) -> StoryValidationResult:
    """:func:`validate_leaf`, with a failure reported as a ``VALIDATION_ERROR``
    flag on that leaf instead of aborting the whole run."""
    try:
        return validate_leaf(doc, job, threshold)
    except Exception as exc:
        return StoryValidationResult(
            story_number=job.number, title=job.title, markdown_file=os.path.basename(job.md_path),
            start_page=job.start_page, end_page=job.end_page, rendered_coverage=0.0,
            raw_coverage=0.0, char_per_page=0.0,
            structural_flags=[f"VALIDATION_ERROR: {type(exc).__name__}: {exc}"],
            threshold=threshold, kind=job.kind, label=job.label, part=job.part, section=job.section,
        )


class ExtractionValidator:
    """Validates on-disk extraction output (Section folders, Introductions) against the PDF."""

    @staticmethod
    def _load_toc(input_dir: str) -> Tuple[List[Tuple[str, Dict[str, Any], Dict[str, Any]]], List[str]]:
        """``[(kind, section_entry, leaf_entry)]`` from a Section manifest, plus flags."""
        toc_path = os.path.join(input_dir, "table_of_contents.json")
        if not os.path.exists(toc_path):
            return [], [f"MISSING_TOC: {toc_path} not found — nothing to validate"]
        try:
            with open(toc_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return [], [f"UNREADABLE_TOC: {toc_path} ({exc})"]

        leaves = [
            (kind, sec, leaf)
            for sec in data.get("sections", [])
            for kind, key in (("story", "stories"), ("essay", "essays"))
            for leaf in sec.get(key, [])
        ]
        if not leaves:
            return [], [f"EMPTY_TOC: no stories or essays listed in {toc_path}"]
        return leaves, []

    @classmethod
    def section_jobs(
        cls, input_dir: str, section: Optional[SectionRange] = None, part_title: str = ""
    ) -> Tuple[List[LeafJob], List[str]]:
        """The leaves listed in a Section folder's manifest, plus manifest flags."""
        leaves, flags = cls._load_toc(input_dir)
        jobs: List[LeafJob] = []
        for kind, sec, leaf in leaves:
            number = int(leaf.get(f"{kind}_number", -1))
            if kind == "story":
                label, errata_key = "", number
                default_file = f"story_{number:03d}.md"
            else:
                label = f"Essay {sec.get('section_id', '?')}.{number}"
                errata_key = label
                default_file = f"essay_{number:02d}.md"
            jobs.append(LeafJob(
                kind=kind,
                number=number,
                title=leaf.get("title", ""),
                label=label,
                md_path=os.path.join(input_dir, leaf.get("markdown_file") or default_file),
                start_page=int(leaf.get("start_page", 0) or 0),
                end_page=int(leaf.get("end_page", 0) or 0),
                toc_entry=leaf,
                errata_key=errata_key,
                part=part_title,
                section=section.full_title if section else sec.get("section_title", ""),
            ))
        return jobs, flags

    @staticmethod
    def introduction_job(output_dir: str, part: PartRange, filename: str) -> Optional[LeafJob]:
        """The Part's Introduction, from the Part's first page to its first Section's."""
        path = os.path.join(output_dir, part.folder_name, filename)
        if not os.path.exists(path):
            return None
        end_page = part.sections[0].start_page if part.sections else part.end_page
        return LeafJob(
            kind="introduction", number=0, title=part.full_title, label="Introduction",
            md_path=path, start_page=part.start_page, end_page=end_page,
            toc_entry={"start_page": part.start_page, "end_page": end_page},
            errata_key=f"Introduction {part.folder_name}", part=part.full_title,
        )

    @staticmethod
    def validate_leaves(
        pdf_path: str,
        jobs: List[LeafJob],
        threshold: float = DEFAULT_THRESHOLD,
        workers: int = 1,
    ) -> List[StoryValidationResult]:
        """Validates ``jobs``, in order. With ``workers`` > 1 leaves are scored in
        parallel processes, largest first; each holds one leaf's text at a time."""
        if not os.path.exists(pdf_path):
            return [_validate_reported(None, job, threshold) for job in jobs]
        if workers <= 1 or len(jobs) <= 1:
            with fitz.open(pdf_path) as doc:
                return [_validate_reported(doc, job, threshold) for job in jobs]

        def size(job: LeafJob) -> int:
            return os.path.getsize(job.md_path) if os.path.exists(job.md_path) else 0

        order = sorted(range(len(jobs)), key=lambda i: size(jobs[i]), reverse=True)
        with ProcessPoolExecutor(workers, initializer=_open_worker_doc, initargs=(pdf_path,)) as pool:
            done = dict(zip(order, pool.map(_validate_in_worker, [(jobs[i], threshold) for i in order])))
        return [done[i] for i in range(len(jobs))]

    @classmethod
    def collect_section(
        cls,
        doc: Optional["fitz.Document"],
        input_dir: str,
        section: Optional[SectionRange] = None,
        part_title: str = "",
    ) -> Tuple[List[LeafJob], List[str], List[str]]:
        """``(jobs, flags, errata)`` for one Section folder: its leaves plus the
        MỤC LỤC count check (skipped without ``doc`` or ``section``)."""
        jobs, flags = cls.section_jobs(input_dir, section, part_title)
        errata: List[str] = []
        if doc is not None and jobs:
            count_flags, errata = check_completeness(
                doc, section, [j.number for j in jobs],
                leaf_kind="essays" if jobs[0].kind == "essay" else "stories",
            )
            flags.extend(count_flags)
        return jobs, flags, errata

    @classmethod
    def collect(
        cls,
        doc: "fitz.Document",
        output_dir: str,
        part: Optional[int] = None,
        section_spec: Optional[str] = None,
    ) -> Tuple[List[LeafJob], List[str], List[str]]:
        """``(jobs, flags, errata)`` for a ``--part`` / ``--section`` selection
        (``None`` = all three Parts), in book order. Each selected Part's
        Introduction is included when no ``section_spec`` narrows it; Section
        flags and errata are prefixed with the Section's path."""
        parts = TableOfContentsParser.parse_parts(doc)
        jobs: List[LeafJob] = []
        flags: List[str] = []
        errata: List[str] = []
        for part_range, sections in TableOfContentsParser.select_parts(parts, part, section_spec):
            if section_spec is None:
                intro = cls.introduction_job(output_dir, part_range, BookPipeline.INTRODUCTION_FILE)
                if intro is not None:
                    jobs.append(intro)
            for section in sections:
                input_dir = os.path.join(output_dir, section.path)
                if not os.path.isdir(input_dir):
                    flags.append(f"MISSING_SECTION: {input_dir} not found "
                                 "(re-run with --extract-first to produce it)")
                    continue
                section_jobs, section_flags, section_errata = cls.collect_section(
                    doc, input_dir, section, part_range.full_title)
                jobs.extend(section_jobs)
                flags.extend(f"{section.path}: {f}" for f in section_flags)
                errata.extend(f"{section.path}: {e}" for e in section_errata)
        return jobs, flags, errata

    @classmethod
    def validate_section(
        cls,
        pdf_path: str,
        input_dir: str,
        threshold: float = DEFAULT_THRESHOLD,
        section: Optional[SectionRange] = None,
        workers: int = 1,
    ) -> Tuple[List[StoryValidationResult], List[str], List[str]]:
        """Validate every leaf in a Section folder.

        Returns ``(results, section_flags, section_errata)``.
        """
        if os.path.exists(pdf_path):
            with fitz.open(pdf_path) as doc:
                jobs, flags, errata = cls.collect_section(doc, input_dir, section)
        else:
            jobs, flags, errata = cls.collect_section(None, input_dir, section)
            if jobs:
                flags.append(f"MISSING_PDF: {pdf_path} not found — alignment scoring skipped")
        return cls.validate_leaves(pdf_path, jobs, threshold, workers), flags, errata


class ValidationReporter:
    """Renders validation results: flagged leaves by Part → Section, then all worst-first."""

    @staticmethod
    def _sorted(results: List[StoryValidationResult]) -> List[StoryValidationResult]:
        # rendered_coverage is the ONLY sort key; raw_coverage is informational.
        return sorted(results, key=lambda r: (r.rendered_coverage, r.part, r.section, r.story_number))

    @staticmethod
    def _shown_flags(r: StoryValidationResult) -> List[str]:
        return r.structural_flags + [f"ERRATUM: {e.split(' — ')[0]}" for e in r.source_errata]

    @classmethod
    def render_markdown(
        cls,
        results: List[StoryValidationResult],
        section_flags: List[str],
        threshold: float = DEFAULT_THRESHOLD,
        section_errata: Optional[List[str]] = None,
    ) -> str:
        section_errata = section_errata or []
        ordered = cls._sorted(results)
        review = [r for r in ordered if r.status == "REVIEW"]
        flagged = [r for r in ordered if r.structural_flags]
        errata = [r for r in ordered if r.source_errata]
        kinds = {k: sum(r.kind == k for r in results) for k in ("story", "essay", "introduction")}

        lines: List[str] = []
        lines.append("# Extraction Validation Report")
        lines.append("")
        lines.append(
            f"- Leaves validated: **{len(results)}** ({kinds['story']} Stories, "
            f"{kinds['essay']} Essays, {kinds['introduction']} Introductions)"
        )
        lines.append(f"- Threshold (rendered_coverage): **{threshold:.2f}**")
        lines.append(f"- Needing review: **{len(review)}**")
        lines.append(f"- With structural flags: **{len(flagged)}**")
        lines.append(f"- Known source errata: **{len(errata)}**")
        lines.append("")
        lines.append(
            "`rendered_coverage` = fraction of the rendered Markdown prose found in the raw PDF "
            "page text (primary metric, sort key, threshold). `raw_coverage` is **informational "
            "only** — adjacent leaves share boundary pages, so it is expected to be noisy."
        )
        lines.append("")

        lines.append("## Section-level checks")
        lines.append("")
        if section_flags:
            for flag in section_flags:
                lines.append(f"- {flag}")
        else:
            lines.append("- No section-level issues.")
        for entry in section_errata:
            lines.append(f"- MỤC LỤC ERRATUM: {entry}")
        lines.append("")

        # Results arrive in book order; keep it for the grouping.
        lines.append("## Flagged by Part and Section")
        lines.append("")
        non_ok = [r for r in results if r.status != "OK"]
        if not non_ok:
            lines.append("- None.")
        part = section = None
        for r in non_ok:
            if r.part != part:
                part, section = r.part, None
                lines.extend(["", f"### {part or '(no Part)'}", ""] if lines[-1] else
                             [f"### {part or '(no Part)'}", ""])
            if r.section and r.section != section:
                section = r.section
                lines.extend(["", f"#### {section}", ""] if lines[-1] else [f"#### {section}", ""])
            lines.append(
                f"- **{r.display_label}** — {r.title} (`{r.markdown_file}`, pp. "
                f"{r.start_page}-{r.end_page}): {r.status} — "
                + ", ".join(r.structural_flags + [e.split(" — ")[0] for e in r.source_errata]
                            or [f"rendered_coverage {r.rendered_coverage:.3f}"])
            )
        lines.append("")

        lines.append("## All leaves (worst first)")
        lines.append("")
        lines.append("| Leaf | Title | Pages | rendered_cov | raw_cov (info) | chars/page | Status | Flags |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in ordered:
            shown = cls._shown_flags(r)
            lines.append(
                f"| {r.display_label} | {r.title} | {r.start_page}-{r.end_page} | "
                f"{r.rendered_coverage:.3f} | {r.raw_coverage:.3f} | {r.char_per_page:.0f} | "
                f"{r.status} | {', '.join(shown) if shown else '-'} |"
            )
        lines.append("")

        lines.append("## Known Source Errata")
        lines.append("")
        lines.append(
            "Flags caused by an error printed in the textbook itself (allow-listed in "
            "`KNOWN_SOURCE_ERRATA`); these leaves are not counted as needing review."
        )
        lines.append("")
        if errata:
            for r in errata:
                lines.append(f"### {r.display_label} — {r.title} (`{r.markdown_file}`)")
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
                lines.append(f"- {r.display_label}: " + "; ".join(r.notes))
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
            f"Validated {len(results)} leaves — {len(review)} need review, "
            f"{len([r for r in ordered if r.structural_flags])} with structural flags, "
            f"{len([r for r in ordered if r.source_errata])} known source errata."
        )
        for flag in section_flags:
            lines.append(f"  [section] {flag}")
        if not ordered:
            lines.append("  (nothing validated)")
            return "\n".join(lines)

        lines.append(f"Worst {min(top_n, len(ordered))} by rendered_coverage:")
        lines.append(f"  {'leaf':>12}  {'rend':>6}  {'raw*':>6}  {'c/pg':>6}  status  title / flags")
        for r in ordered[:top_n]:
            shown = cls._shown_flags(r)
            flags = (" | " + ", ".join(shown)) if shown else ""
            lines.append(
                f"  {r.display_label:>12}  {r.rendered_coverage:>6.3f}  {r.raw_coverage:>6.3f}  "
                f"{r.char_per_page:>6.0f}  {r.status:<6}  {r.title}{flags}"
            )
        lines.append("  (* raw_coverage informational only — noisy on shared boundary pages)")
        return "\n".join(lines)
