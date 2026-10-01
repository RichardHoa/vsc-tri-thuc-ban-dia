# Kho Tàng Truyện Cổ Tích Việt Nam — local reading collection

## Problem Statement

The digitized text of "Kho Tàng Truyện Cổ Tích Việt Nam" (Nguyễn Đổng Chi) — 201 stories across 10 sections, already extracted to markdown in this repo — has no way to be read on the `digitizing-vietnam-website` frontend. A reader who wants to browse or search these stories, follow scholarly footnotes, or read the comparative-variant (KHẢO DỊ) notes attached to a story currently has no UI for any of that; the content only exists as files on disk.

Separately, the frontend's collection system is Strapi-backed end to end (a `collections` CMS row drives both the `/our-collections` listing tile and the collection-detail header), so there is currently no way to ship a browsable collection whose CMS entry doesn't exist yet — which blocks getting this content in front of readers before the Strapi-side content work is done.

## Solution

Add a new "Kho Tàng Truyện Cổ Tích Việt Nam" card to `/our-collections`, using the already-extracted markdown as its content. Clicking it opens a two-pane reader (list + detail), modeled on the existing `tho-ho-xuan-huong/tinh-hoa-mua-xuan` reading experience: a left panel for finding a story (search by title, filter by section I–X) and a right panel that renders the selected story, with footnotes opening a citation popover exactly like the Hán-Nôm dictionary lookup already in use on that page.

Because no Strapi record exists for this collection yet, the listing tile and collection-detail header are driven by a temporary, in-code stand-in (obvious placeholder title/abstract) rather than CMS content — clearly marked in code as removable once a real Strapi entry is created.

## User Stories

1. As a reader browsing `/our-collections`, I want to see a card for "Kho Tàng Truyện Cổ Tích Việt Nam" with its book cover, so that I know this collection exists and can open it.
2. As a reader, I want that card to sit in whatever bucket collections without categories land in (today, "Uncategorized"), so that the listing page doesn't break its existing grouping logic for an uncategorized entry.
3. As a reader, I want the card to render correctly in every existing view mode of `/our-collections` (grid, list, TOC), so that the new collection behaves like every other one already there.
4. As a reader who opens the collection, I want a list of all 201 stories, so that I can see the full scope of what's available.
5. As a reader, I want the story list grouped by section (I–X) when no filter is applied, so that 201 items are navigable rather than one undifferentiated wall of text.
6. As a reader, I want to filter the story list down to a single section, so that I can browse just the stories I care about (e.g., only origin myths, only humorous tales).
7. As a reader, I want to search the story list by title substring, so that I can jump straight to a story if I already know roughly what it's called.
8. As a reader, I want a sensible default story shown when I first open the collection (no story explicitly selected yet), so that the right panel isn't blank on first load.
9. As a reader, I want clicking a story in the left panel to load it in the right panel without a full page navigation, so that browsing feels fast.
10. As a reader, I want the currently-open story reflected in the URL, so that I can share or bookmark a link directly to that story.
11. As a reader, I want the story's main narrative text to render as readable prose (not raw markdown), so that the reading experience matches the rest of the site's typography.
12. As a reader, I want verse/poem passages within a story to render in a visually distinct panel (not default blockquote styling), so that poems are recognizable as poems.
13. As a reader, I want the same verse styling to apply inside a footnote's popover if that footnote itself contains verse, so that the presentation is consistent wherever poem text appears.
14. As a reader, I want footnote markers in the story text to appear as small clickable numerals, so that I can tell which passages have scholarly annotations.
15. As a reader, I want clicking a footnote numeral to open a popover with that footnote's own text, so that I can read the annotation without leaving the page or losing my place.
16. As a reader, I want each footnote numeral to open the *correct* footnote text — not have several different numerals collapse onto the same definition — even though the source material numbers footnotes per printed page (so the same label like `[^1]` repeats many times within one story), so that citations are trustworthy.
17. As a reader, I want the footnote popover's open/close animation to match the existing Hán-Nôm dictionary popover elsewhere on the site, so that the interaction feels like a consistent part of the same product.
18. As a reader, I want a story's KHẢO DỊ (comparative-variant) section, when present, to be included in the readable text with its own footnotes working the same way as the main narrative's, so that I don't lose scholarly content specific to variant tellings.
19. As a reader encountering one of the small number of stories where the source extraction has a footnote-numbering defect (a marker with no matching definition), I want that marker to render as plain text rather than a broken link or a crash, so that the one imperfect story doesn't degrade my ability to read everything else.
20. As the developer eventually integrating a real Strapi entry for this collection, I want the temporary in-code stand-in (listing tile object, collection-detail header short-circuit) clearly commented as removable, so that finishing the CMS-side work is a clean deletion, not an archaeology exercise.
21. As a developer maintaining the extraction pipeline, I want a build-time warning identifying every story with a footnote-count mismatch, so that I can find and manually fix the underlying data defect later without re-deriving the list from scratch.

## Implementation Decisions

- **Content source of truth**: the 10 section folders and 201 `story_NNN.md` files under this repo's `extracted_stories/`, each section carrying a `table_of_contents.json` manifest (story number, title, page range, filename, `has_khao_di`, `footnote_count`). This data is copied verbatim into the frontend's public assets; no new manifest is hand-authored — the per-section `table_of_contents.json` files are aggregated at runtime into the story index.
- **No Strapi changes in this PR.** The collection-listing tile is a synthetic, in-code object matching the shape the listing page already expects (title, abstract, slug, thumbnail formats, empty category/language/subject/resource-type arrays so existing filter logic doesn't throw). The collection-detail route's existing static-collection bypass (which today only skips fetching a collection's *item list* from Strapi, not its header metadata) is extended so this one slug also skips the Strapi metadata fetch, substituting a locally-defined object shaped like the real metadata response so the shared header component renders unchanged. Both stand-ins carry an explicit "TEMPORARY — remove once a real Strapi record exists" comment.
- **Placeholder copy** (collection abstract, item-detail header title/abstract) is bluntly, obviously placeholder text (e.g. "Tiêu đề tạm thời") rather than realistic-sounding filler, so nobody mistakes it for finished copy.
- **No locale/translation handling.** Content is pure Vietnamese and is shown identically under every locale route, matching how other local, non-Strapi-item collections behave today.
- **Section filter UI** reuses the existing tabbed categories+grid interaction pattern already used elsewhere in the collection-listing view, rather than introducing a dropdown-style picker — an "All" tab plus one tab per section (I–X).
- **Footnote citation UI** reuses the existing popover component and its established open/close animation (the same one driving the Hán-Nôm dictionary lookup interaction), rather than any new popover/tooltip implementation.
- **Markdown rendering uses no new dependency.** The extraction pipeline (`extractor/formatters.py`) only ever produces a narrow, known markdown subset for this content — `#`/`##`/`###` headings, plain-text paragraphs, `> `-prefixed blockquote lines for verse, and the `[k](#fn-idx)` footnote-reference links this feature itself generates — with no tables, strikethrough, or other inline formatting. A small hand-written function splits the markdown into blocks and renders each according to type, with a tiny inline matcher that turns footnote-reference links into clickable footnote numerals instead of navigable anchors; nothing else needs handling.
- **Footnote parsing is position-based, not label-based.** The source numbers footnotes per printed page, so a label like `[^1]` recurs many times within a single story; the k-th footnote marker encountered in reading order (main body, followed by the KHẢO DỊ section when present) is paired with the k-th footnote definition in that story's definitions section, regardless of what numeral label either one carries. The definitions section is located by a delimiter pattern tolerant of the blank-line formatting actually present in the source (rather than an exact literal string match).
- **KHẢO DỊ handling**: when present, this comparative-variant section is textually part of "the body" for footnote-counting purposes — it precedes the footnote-definitions section in the source and its own footnote markers are counted in the same continuous sequence as the main narrative's.
- **Mismatched footnote counts are handled defensively, not fixed at the source in this PR.** For any story where the number of footnote markers exceeds the number of parsed definitions, markers beyond the last available definition render as plain, non-interactive text rather than a broken link. A build-time console warning names every story slug where this occurs, so the underlying extraction defect (11 known stories, caused by same-page footnotes occasionally merging into one definition block during extraction) can be triaged and fixed later as separate, source-data work — out of scope here.
- **Default selection**: opening the collection with no story explicitly chosen shows the first story of the first section; the section filter affects only which stories are listed, never which one is initially open.
- **Grouping**: the "All" (unfiltered) story list is grouped by section with visible section headers; a single-section filter shows a flat list for that section only.

## Testing Decisions

- No automated test seam is introduced for this feature. `digitizing-vietnam-website` has no test runner, configuration, or existing test files of any kind today, and adding one is judged out of scope for a single-collection feature.
- Verification is manual, via the running dev server: exercising the listing card, the collection-detail view, the two-pane reader (search, section filter, selection, URL sync), the footnote-popover interaction on a story with clean footnote/definition counts, the same interaction on a story with a known footnote-count mismatch (confirming graceful plain-text fallback plus the console warning), verse rendering both inline and inside a footnote popover, and a final lint pass.
- If a test runner is introduced in a future PR, the highest-value seam for this feature would be the pure footnote-parsing function (input: raw story markdown; output: body text plus an ordered footnote-definition list) — it has no I/O and is where the trickiest domain logic (position-based matching, the KHẢO DỊ boundary, the mismatch fallback) lives. No prior art exists in this repo for this kind of pure-function test, since no tests exist yet.

## Out of Scope

- Creating the real Strapi `collections` record, thumbnail, categories, and abstract for this collection — the in-code stand-ins here are explicitly temporary and are expected to be deleted once that CMS work lands.
- Fixing the 11 stories with footnote-count mismatches in the source extraction data — flagged via a build-time warning for manual follow-up, not corrected in this PR.
- Introducing a test runner/framework to this frontend repo.
- Any translation or locale-specific content variation.
- Real (non-placeholder) header title/abstract copy for the collection or its item-detail page.

## Further Notes

- This spec folds in a fact-finding/grilling pass conducted against both the extraction repo (`vsc-tri-thuc-ban-dia`) and the frontend repo (`digitizing-vietnam-website`); see `.scratch/kho-tang-truyen-co-tich-viet-nam/plan.md` for the fuller narrative of what was checked and why, including the exact set of 11 mismatched story slugs.
- Two domain terms are introduced by this feature and should eventually be folded into the project's glossary: **Chú thích** (a story's footnote-definitions section) and **KHẢO DỊ** (an optional in-body appendix of comparative variant tellings, preceding the footnote-definitions section).
