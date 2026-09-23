"""
Extraction Accuracy Validator.

Read-only quality checks over already-extracted folk-story output. Never mutates
extraction results: it reads `table_of_contents.json` + `story_NNN.md` from a
section output directory, re-reads the raw PyMuPDF page text for each story's
page range, and scores text fidelity with `difflib`.

Two kinds of signal are produced:

* **Structural checks** — empty title/category/body, orphan footnote markers,
  orphan footnote entries, low character density, section-level story-count drift.
* **Text alignment** — `rendered_coverage` (what fraction of the rendered Markdown
  prose is found in the raw PDF page text) is the primary metric and the report's
  sort key / threshold. `raw_coverage` is **informational only**: adjacent stories
  share PDF boundary pages, so a story's page range legitimately contains a
  neighbour's text and raw coverage is inherently noisy. It must never be used to
  fail or sort a story.

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

from .normalizer import TextNormalizer
from .toc import SectionRange, TableOfContentsParser

#: Below this many characters per PDF page a story is flagged ``LOW_DENSITY``.
MIN_CHARS_PER_PAGE = 800

DEFAULT_THRESHOLD = 0.90


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

    @property
    def status(self) -> str:
        """``REVIEW`` when below threshold or structurally flagged, else ``OK``."""
        if self.rendered_coverage < self.threshold or self.structural_flags:
            return "REVIEW"
        return "OK"


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


def strip_markdown_scaffolding(md: str) -> str:
    """Drop Markdown scaffolding, leaving only prose that should exist in the PDF.

    Removes heading lines, the ``---`` rule, the ``### Chú thích`` label, the
    ``[^N]: (Trang N)`` footnote prefixes and inline ``[^N]`` markers. Footnote
    *body* text is kept — it is real PDF text.
    """
    kept: List[str] = []
    for line in md.splitlines():
        if _HRULE_RE.match(line):
            continue
        if _HEADING_RE.match(line):
            # Headings (category, story title, KHẢO DỊ, Chú thích) are scaffolding.
            continue
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


# ---------------------------------------------------------------------------
# Section B — structural checks
# ---------------------------------------------------------------------------


def parse_markdown_story(path: str) -> Dict[str, Any]:
    """Parse a rendered ``story_NNN.md`` into its structural parts.

    Returns ``{title, category, body, footnotes: List[Tuple[orig_num, page]],
    khao_di_present: bool}``. Missing/unreadable files yield empty structures
    rather than raising (the CLI is a reporting tool, never a crasher).
    """
    parsed: Dict[str, Any] = {
        "title": "",
        "category": "",
        "body": "",
        "footnotes": [],
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
    for line in md.splitlines():
        stripped = line.strip()
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
            parsed["footnotes"].append((int(match.group(1)), page))
            continue
        if _HRULE_RE.match(line) or stripped.startswith("#"):
            continue
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

                rendered = normalize_for_diff(
                    strip_markdown_scaffolding(parsed.get("raw_markdown", ""))
                )
                page_span = max(1, end_page - start_page + 1)
                char_per_page = len(rendered) / page_span

                if char_per_page < MIN_CHARS_PER_PAGE:
                    flags.append("LOW_DENSITY")

                if doc is not None and rendered:
                    raw = extract_raw_page_text(doc, start_page, end_page)
                    rendered_cov, raw_cov = score_alignment(raw, rendered)
                    del raw  # bound memory: never hold two stories' raw text
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

        lines: List[str] = []
        lines.append("# Extraction Validation Report")
        lines.append("")
        lines.append(f"- Stories validated: **{len(results)}**")
        lines.append(f"- Threshold (rendered_coverage): **{threshold:.2f}**")
        lines.append(f"- Needing review: **{len(review)}**")
        lines.append(f"- With structural flags: **{len(flagged)}**")
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
            flags = ", ".join(r.structural_flags) if r.structural_flags else "-"
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
            f"{len([r for r in ordered if r.structural_flags])} with structural flags."
        )
        for flag in section_flags:
            lines.append(f"  [section] {flag}")
        if not ordered:
            lines.append("  (no stories found)")
            return "\n".join(lines)

        lines.append(f"Worst {min(top_n, len(ordered))} by rendered_coverage:")
        lines.append(f"  {'#':>4}  {'rend':>6}  {'raw*':>6}  {'c/pg':>6}  status  title / flags")
        for r in ordered[:top_n]:
            flags = (" | " + ", ".join(r.structural_flags)) if r.structural_flags else ""
            lines.append(
                f"  {r.story_number:>4}  {r.rendered_coverage:>6.3f}  {r.raw_coverage:>6.3f}  "
                f"{r.char_per_page:>6.0f}  {r.status:<6}  {r.title}{flags}"
            )
        lines.append("  (* raw_coverage informational only — noisy on shared boundary pages)")
        return "\n".join(lines)
