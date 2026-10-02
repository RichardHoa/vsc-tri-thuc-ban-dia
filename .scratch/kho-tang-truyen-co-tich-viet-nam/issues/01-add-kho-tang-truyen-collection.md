# 01: Add "Kho Tàng Truyện Cổ Tích Việt Nam" collection (local-only, no Strapi changes)

**What to build:** From a reader's perspective on `digitizing-vietnam-website`: a new collection card on `/our-collections` for the already-extracted "Kho Tàng Truyện Cổ Tích Việt Nam" book (201 stories, 10 sections), with no Strapi record backing it yet. Clicking it opens a two-pane reader — a left panel to search by title and filter by section (I–X), grouped by section when unfiltered, defaulting to the first story of the first section — and a right panel rendering the selected story, with verse shown in a distinct panel and footnote markers opening a popover with the correctly position-matched citation text (matching by reading order, not by the source's repeating per-page labels). Selecting a story updates the URL so it's shareable. The listing tile and collection-detail header use temporary, clearly-commented in-code stand-ins in place of Strapi data, removable once a real CMS entry exists. Full context: `.scratch/kho-tang-truyen-co-tich-viet-nam/spec.md` (problem statement, user stories, implementation/testing decisions) and `.scratch/kho-tang-truyen-co-tich-viet-nam/plan.md` (step-by-step plan, exact delimiter regex, the 11 known mismatched-footnote-count story slugs, file/component references).

**Blocked by:** None (can start immediately)

**Status:** resolved

- [ ] New collection card renders on `/our-collections` with the book cover, correctly bucketed among uncategorized collections, across all existing view modes (grid/list/TOC).
- [ ] Collection-detail and item-detail routes render with no new Strapi record, via in-code stand-ins clearly commented `TEMPORARY — remove once a real Strapi record exists`.
- [ ] Reader lists all 201 stories, grouped by section when unfiltered, filterable to a single section, and searchable by title substring; selecting a story updates the right panel and the URL.
- [ ] Footnote numerals are clickable and open a popover with the correct, position-matched citation text — verified on both a clean story (`story_002`, 6 markers / 6 defs) and a known mismatched one (`story_108`, 4 markers / 3 defs: the unmatched marker renders as plain text, not a broken link, and a console warning names the slug).
- [ ] Verse renders in a distinct panel (not default blockquote styling), both in story bodies and inside footnote popovers.
- [ ] Footnote popover open/close animation matches the existing Hán-Nôm dictionary popover elsewhere on the site.
- [ ] `npm run lint` passes on new/changed files; no remaining reference to the old repo-root `book.jpg` path.

## Comments
- 2026-10-02 (developer, via agent): Resolved: finished.
