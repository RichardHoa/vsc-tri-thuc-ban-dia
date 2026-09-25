# Folk-story extraction pipeline: dialogue fix, poem formatting, validator coverage, full I–X extraction

Status: ready-for-agent

## Context

This repo (`vsc-tri-thuc-ban-dia`) extracts the Vietnamese folk-tale anthology *Kho Tàng Truyện Cổ Tích Việt-Nam* (`data.pdf`) into per-story Markdown via `extract_folk_stories.py` (library code in `extractor/`), then checks the output against the source PDF via `validate_extraction.py`. Read `docs/ai-context/spec.md` and `docs/ai-context/project-structure.md` first — they document the module responsibilities, CLI contracts, and the project's invariants (Vietnamese diacritics are never stripped/folded; `extractor/` never mutates `data.pdf`; `validate_extraction.py` is a reporting tool that always exits 0). This document does not repeat those invariants — follow them.

Only sections I–III (61 stories) are extracted today, into `extracted_stories/{I,II,III}_*/`. `data.pdf`'s MỤC LỤC (table of contents) defines 10 Roman-numeral sections under "PHẦN THỨ HAI", confirmed via `python3 extract_folk_stories.py --list-sections`:

```
 1. I. NGUỒN GỐC SỰ VẬT                             (pages 86-203)
 2. II. SỰ TÍCH ĐẤT NƯỚC VIỆT                        (pages 204-254)
 3. III. SỰ TÍCH CÁC CÂU VÍ                          (pages 255-414)
 4. IV. THÔNG MINH TÀI TRÍ VÀ SỨC KHỎE               (pages 415-578)
 5. V. SỰ TÍCH ANH HÙNG NÔNG DÂN                     (pages 590-633)
 6. VI. TRUYỆN PHÂN XỬ                               (pages 634-690)
 7. VII. TRUYỆN THẦN TIÊN MA QUỶ VÀ PHÙ PHÉP         (pages 691-900)
 8. VIII. TRUYỆN ĐỀN ƠN TRẢ OÁN                      (pages 901-1122)
 9. IX. TÌNH BẠN, TÌNH YÊU VÀ NGHĨA VỤ               (pages 1123-1255)
10. X. TRUYỆN VUI TƯƠI DÍ DỎM                        (pages 1256-1338)
```

"Section 1 to 10" in this document always means these 10 `--section` indices, not story numbers.

Three problems drive this work:

1. **Bug**: `extracted_stories/III_SU_TICH_CAC_CAU_VI/story_041.md` renders a dialogue dash on its own line, orphaned from the quoted text that should follow it on the same line.
2. **Feature**: verse (poems) embedded in the source text render as ordinary prose paragraphs; they need distinct Markdown formatting.
3. **Feature**: `extractor/validation.py`'s structural checks don't cover several edge cases that exist in the PDF (poems, long multi-page footnotes, dialogue broken across a page boundary) and need to before sections IV–X — 1,150+ pages never seen by this pipeline — are extracted.

## Root causes (already diagnosed — do not re-derive, verify then fix)

### 1. Dialogue dash orphaned across a page boundary

In the raw PDF, page 307's last body line ends `"...Ngốc hỏi: -"` and page 308's first body line is `"Mua hả?". Lá vẫn đung đưa..."`. Verify with:

```python
import fitz
doc = fitz.open("data.pdf")
print(doc[306].get_text())  # page 307, ends "...hỏi: -"
print(doc[307].get_text())  # page 308, starts "\"Mua hả?\". Lá vẫn..."
```

`extractor/engine.py`, `StoryExtractionEngine.extract_single_story` (~line 118-132): a text block is classified `is_dialogue` when it starts with `-`, contains `": -"`, or contains `". -"`. On `is_dialogue`, the engine immediately calls `flush_current_paragraph()` and appends `TextNormalizer.split_dialogues(combined_block_text)` straight into `paragraphs` — there is no mechanism carrying an unresolved trailing dialogue marker across the page-loop iteration (`for pno in range(story_def.start_page - 1, story_def.end_page)`, line 51). So the block ending in a bare `-` at the bottom of page 307 is split into its own paragraph (`["Ngốc ta... hỏi:", "-"]`) and flushed before page 308 is ever read; page 308's first block then starts a brand-new paragraph accumulation with no memory that a dialogue was left open.

The non-dialogue path (lines 133-142) *does* have continuation logic (`TextNormalizer.ends_sentence` check appends to `current_para_lines` instead of flushing) — the dialogue path needs the equivalent: **when a flushed dialogue line's last element is a bare `-` (or otherwise doesn't end in terminal punctuation per `TextNormalizer.ends_sentence`), it must not be treated as a complete paragraph yet.** Hold it (e.g. in a new `pending_dialogue_prefix: Optional[str]` carried across the page loop, not just within one page's block loop) and prepend it to the next non-empty text encountered — dialogue or narrative — before that text is split/appended.

Fix this in `engine.py` (and `normalizer.py`'s `split_dialogues`/`ends_sentence` if the split logic needs to expose a "did this line end unterminated" signal). This must work regardless of which page happens to end mid-dialogue — a general fix, not a special case for story 41.

### 2. Poems render as prose

Confirmed on PDF page 102 (a footnote, inside a story in section I — poems are not confined to body text) via block/line geometry (`page.get_text("dict")`):

```
x0= 98.6  font=Times-Roman         "Có người kể: cháu sau đó cũng chết hóa làm chim tu hú...kêu lên: "
x0=279.4  font=Times-Italic        "Cô hố cô hố. "
x0=283.7  font=Times-Italic        "Lúa đã trổ, "
x0=282.2  font=TimesNewRoman,Italic "Đỗ đã chín, "
x0=272.9  font=Times-Italic        "Bay về mà ăn!2 "
```

Verse lines in this book are set in an **italic font** (`Times-Italic` / `TimesNewRoman,Italic`) and **indented** (~x0 270-290 vs. ~x0 87-99 for body prose). This is the primary detection signal — it must be read from `page.get_text("dict")` span/line metadata (font name containing `Italic`/`Oblique`, and/or `x0` well past the body-text left margin), not from any textual heuristic on the extracted string, since by the time text reaches `engine.py`'s `combined_block_text` the font/position information for individual lines has already been discarded. This means poem detection has to happen where `engine.py` currently reads `l['spans']` per line (~line 67-93), before that geometry is thrown away — Phase 0's survey (below) should confirm this signal holds across sections IV-X (font names might vary book-wide) before Phase 1 builds detection on it.

Target output format (per the "grill" decision): a Markdown blockquote, one verse line per `>` line, e.g.:

```markdown
> Cô hố cô hố.
> Lúa đã trổ,
> Đỗ đã chín,
> Bay về mà ăn!
```

This must render inline in the flow of the surrounding paragraph, not be pulled into a separate section — a poem quoted mid-narrative stays where the narrative places it (do not move poems to an appendix or footnote-only area).

### 3. Validator coverage gaps

`extractor/validation.py`'s current structural checks (`check_structure`, `check_completeness`) do not know about:
- Poems (new in this work — see above): once poems render as blockquotes, `strip_markdown_scaffolding`/`split_rendered_segments` (validation.py) must be taught to treat `> line` the same way they already treat plain prose lines for `rendered_coverage` diffing (currently `_HRULE_RE`/`_HEADING_RE` strip scaffolding; blockquote markers need the same treatment: strip the leading `> ` before diffing against raw PDF text, don't drop the line).
- Long multi-page footnotes (e.g. story 41's `[^1]` spans pages 296-311, 11 entries) — currently these are separate `Footnote` entries per page, which the "grill" round confirmed should **stay separate** (each keeps its own `(Trang N)` tag), but there's no check that the chain is *complete*: no skipped page, no continuation that lost its number.
- Dialogue broken across a page boundary (the bug above) — once fixed, there should be a check that would have caught this class of bug (e.g.: no paragraph in the rendered Markdown consists solely of a bare `-`).

## Plan

Work through these phases in order. Do not start Phase N+1 until Phase N is committed and, where applicable, validated.

### Phase 0 — Edge-case survey (build a permanent tool)

Add `extractor/survey.py` (new module) with a CLI entry (either a new top-level `survey_data.py` script, matching the existing `extract_folk_stories.py`/`validate_extraction.py` top-level-script pattern, or a `--survey` flag on one of them — your call, but it must be a real, reusable, committed tool, not a throwaway script, because Phase 1 and Phase 2 both need the same detection logic it develops).

It must scan the full PDF page range covering sections I–X (pages 86-1338, from `TableOfContentsParser.parse_sections`) and report, per page:
- **Poem candidates**: runs of consecutive lines in italic font and/or indented past the body-text left margin (confirm the actual margin/font-name values empirically per section — don't assume section I's numbers hold everywhere).
- **Long-footnote spans**: same footnote number recurring across N consecutive pages (threshold: your judgment, but story 41's 11-page span must trigger it).
- **Dialogue page-boundary breaks**: a page's last body line ending in a bare `-` (optionally followed only by whitespace), or more generally any block whose text ends immediately after a dialogue-opening dash with no quoted content following on the same page.

Output a catalog (e.g. `docs/ai-context/` is for present-tense system docs, not this — write the catalog as `.scratch/folk-story-pipeline-fixes/edge-case-catalog.md`, an artifact of this effort, not permanent system documentation) listing every page/section where each pattern was found, so Phase 1's fixes and Phase 2's validator checks can be verified against real instances beyond the ones already known (story 41's dash break, page 102's poem).

Review the catalog before moving on — if it surfaces a 4th edge-case class not anticipated here, stop and report it rather than silently absorbing it into Phase 1/2's scope.

### Phase 1 — Pipeline fixes

1. Fix the dialogue page-boundary bug in `extractor/engine.py` (and `normalizer.py` if needed) per the root-cause analysis above. Write/run against story 41 to confirm `- \n\n"Mua hả?"` becomes `- "Mua hả?".` on one line, and re-check every other instance the Phase 0 survey found.
2. Add poem detection + blockquote rendering. This likely touches:
   - `extractor/engine.py` (read font/position metadata per line before it's discarded, tag verse lines)
   - `extractor/models.py` (`StoryContent`/paragraph representation may need to carry "this text is verse" rather than being a bare string, depending on your design — keep it minimal)
   - `extractor/formatters.py` (`MarkdownRenderer.render` — emit `> line` for tagged verse lines instead of a plain paragraph)
   Verify against PDF page 102 and every other poem the Phase 0 survey found — including verse found inside footnote text, not only body paragraphs.
3. Do **not** change `extractor/footnotes.py`'s per-page-split behavior for multi-page footnotes — that stays as-is per the "grill" decision.

### Phase 2 — Validator extension

In `extractor/validation.py`:
1. Teach `strip_markdown_scaffolding` / `split_rendered_segments` to strip a leading `> ` the same way they already strip footnote-definition prefixes, so `rendered_coverage` diffing isn't broken by the new blockquote syntax.
2. Add a structural check for footnote-chain completeness: for any footnote number that recurs across multiple pages, its page sequence must be contiguous (or at least monotonically consistent with the story's page range) with no gap — flag `REVIEW` with a note like existing structural flags (e.g. `ORPHAN_MARKER:N` is the existing naming convention in `check_structure`; follow it, e.g. `FOOTNOTE_GAP:N`).
3. Add a structural check that no rendered paragraph is a bare `-` (i.e., confirm Phase 1's fix actually holds project-wide, not just for story 41) — this is a regression guard, not just a design nicety.
4. New checks are structural checks at the same severity as existing ones: they set `REVIEW` status via `structural_flags`, per `docs/ai-context/spec.md`'s existing convention. Do not introduce a different severity tier.
5. Re-run `validate_extraction.py --section 1-3` (i.e. I-III, already extracted) after Phase 1's fixes land, to confirm `rendered_coverage` doesn't regress and the new checks don't spuriously flag clean stories.

### Phase 3 — Full extraction, sections I through X, one at a time

For each section index 1 through 10, in order:

```
python3 extract_folk_stories.py --section N --output-dir extracted_stories
python3 validate_extraction.py --section N --output-dir extracted_stories
```

(Confirm exact flags against `docs/ai-context/spec.md`'s CLI Contracts section and `--help` — reproduce them faithfully, don't guess.)

Regenerate sections I-III (overwriting the current output) as well as extracting IV-X fresh — I-III must be regenerated because Phase 1's fixes could reveal the same latent bugs there that Phase 0's survey found being addressed only in isolation.

**After each section's validation report is produced, inspect it before extracting the next section.** If any story in that section is flagged `REVIEW`, stop — do not proceed to the next section. Write a short summary of what's flagged and why (referencing the specific check that fired) as a comment appended to this file under a `## Comments` heading, and stop for human review. Only continue to the next section once a section comes back clean (no `REVIEW`-flagged stories).

If all 10 sections extract clean, the final state should have `extracted_stories/{I,II,...,X}_*/` for every section, each with its own `table_of_contents.json` and `validation_report.md`, and no outstanding `REVIEW` flags anywhere in the corpus.

## Out of scope

- No changes to `extractor/toc.py`'s section-boundary resolution logic unless Phase 0's survey finds it's wrong for IV-X (report if so, don't silently patch scope creep in).
- No change to the `DEFAULT_THRESHOLD = 0.90` coverage threshold — not part of this effort.
- No remote-LLM judge pass (already documented as deferred/out-of-scope in `extractor/validation.py`'s module docstring).
- Don't touch the root-level `I_stories/` directory if it exists — it's an older/alternate output shape per `docs/ai-context/project-structure.md`; this effort's canonical output is `extracted_stories/<ROMAN>_<SLUG>/` via `--section`.

## Definition of done

- [ ] Phase 0 survey tool committed, edge-case catalog written to `.scratch/folk-story-pipeline-fixes/edge-case-catalog.md`
- [ ] Dialogue page-boundary bug fixed in the pipeline (not hand-patched in one file), verified against story 41 and every other instance the survey found
- [ ] Poems render as blockquotes, verified against page 102 and every other instance the survey found, including verse inside footnotes
- [ ] Validator extended with footnote-chain-completeness and bare-dash-paragraph checks, at existing `REVIEW` severity, and taught to diff blockquote lines correctly
- [ ] Sections I-III regenerated and re-validated clean
- [ ] Sections IV-X extracted and validated one at a time, in order, with a stop-and-report on the first `REVIEW` flag in any section
- [ ] `docs/ai-context/progress.md` updated per this repo's `/update-docs` convention once the above is complete (CLAUDE.md §5: fold shipped work into `spec.md`/`progress.md`, present tense, no changelog narrative)
