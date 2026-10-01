# Kho Tàng reader as the `truyen-co-tich-viet-nam` Collection Item — full Book

**Status:** ready-for-agent

Repo: `digitizing-vietnam-website`. Glossary: that repo's `CONTEXT.md` (Collection, Collection Item, Item Viewer, Book, Part, Section, Story, Essay, Part Introduction, Entry, Khảo dị, Footnote).

Supersedes `.scratch/kho-tang-truyen-co-tich-viet-nam/` (the stand-in collection + `doc-truyen` reader), which is abandoned.

## Problem Statement

The Kho Tàng reader was built as a stand-alone collection (`/our-collections/kho-tang-truyen-co-tich-viet-nam/doc-truyen`) with placeholder title, abstract and listing card, because no Strapi record existed. A developer has since created the real Strapi Collection Item `truyen-co-tich-viet-nam` (vi: "Kho tàng Truyện cổ tích Việt Nam", en: "Treasury of Vietnamese Folktales") inside the `vietnamese-folk-literature` Collection. On that item's page readers see an empty Mirador viewer — the item has no IIIF images — instead of the book's text, and the site now has two competing entry points for the same book, one of them full of placeholder copy.

The data also outgrew the reader. The extraction now covers the whole Book: three Parts, Part Introductions, Phần thứ hai's 201 Stories, and 23 Essays across Phần thứ nhất and Phần thứ ba, organised under a single root table of contents. The reader only knows the old flat ten-Section, Stories-only layout. Its Story-filename addressing and I–X Section tabs can't represent the Book: Essay numbers restart in every Section, and Section numerals IV and V exist in both Phần thứ hai and Phần thứ ba.

## Solution

The `truyen-co-tich-viet-nam` Collection Item page shows the Kho Tàng reader in place of Mirador. Its title, abstract, breadcrumb and metadata block come from Strapi like every other Collection Item. The reader covers the whole Book: a contents panel with one tab per Part, each listing its Part Introduction and then its Sections' Entries; title search across the Book; previous/next navigation in book order; and every Entry addressable by a readable `?muc=` link. The old stand-alone collection, its placeholder listing card and its reader route are removed, so the old URL returns 404. The reader's interface text is localised (vi/en); the Book's text stays Vietnamese.

## User Stories

1. As a reader on the `vietnamese-folk-literature` Collection, I want the "Kho tàng Truyện cổ tích Việt Nam" Collection Item to open a readable text instead of an empty image viewer, so that I can actually read the book.
2. As a reader, I want the item page's title, abstract and breadcrumb to show the real Strapi content, so that I'm not looking at placeholder copy.
3. As a reader, I want the breadcrumb to link back to "Văn học Dân gian Việt Nam", so that I can return to the Collection the book belongs to.
4. As a reader, I want the standard metadata block (languages, publisher, date, etc.) below the reader, so that the page matches every other Collection Item.
5. As a reader browsing `/our-collections`, I want no duplicate placeholder "Kho Tàng" card, so that the book appears only through its real Collection.
6. As a reader who has an old `/our-collections/kho-tang-truyen-co-tich-viet-nam/...` link, I get a 404 (the stand-alone page was never public, so no redirect is kept).
7. As a reader, I want to read Phần thứ nhất's research Essays, so that I can follow Nguyễn Đổng Chi's theory of the folktale.
8. As a reader, I want to read Phần thứ hai's 201 Stories, so that I can read the folktales themselves.
9. As a reader, I want to read Phần thứ ba's assessment Essays, so that I can read the author's conclusions.
10. As a reader, I want to read each Part Introduction, so that I get the author's framing before a Part's Sections.
11. As a reader, I want the contents panel to show one tab per Part, labelled "Phần 1 / 2 / 3" (vi) or "Part 1 / 2 / 3" (en), so that I can switch Parts quickly.
12. As a reader, I want a Part tab's full title as a tooltip and as a line under the tabs, so that I know what the Part is about without the tab being unreadably long.
13. As a reader, I want each Part's list to start with its Part Introduction (labelled "Lời dẫn" / "Introduction") when it has one, then its Sections in order, so that the list mirrors the book.
14. As a reader, I want each Section's Entries grouped under the Section's title, so that I can see the book's structure.
15. As a reader, I want Phần thứ ba's Sections shown as IV and V exactly as printed, so that the reader is faithful to the source even though Phần thứ hai also has a IV and V.
16. As a reader, I want each Story and Essay listed with its printed number and title, so that I can match it with a printed copy.
17. As a reader, I want the currently open Entry highlighted in the list, and the list showing its Part, so that I know where I am.
18. As a reader, I want to search Entry titles across the whole Book, regardless of the active Part tab, so that I can find a Story or Essay without knowing which Part it's in.
19. As a reader, I want search to ignore Vietnamese diacritics and case ("su tich" finds "Sự tích"), so that I can type quickly.
20. As a reader, I want search results grouped under their Part and Section, so that identically numbered Essays from different Sections are distinguishable.
21. As a reader, I want a "no matching entries" message when search finds nothing, so that an empty list isn't confusing.
22. As a reader, I want every Entry to have its own shareable URL via `?muc=`, so that I can link someone straight to a Story or Essay.
23. As a reader, I want those URLs to be readable — `truyen-62`, `phan-1-muc-ii-bai-3`, `phan-3-loi-dan` — so that the link says what it points to.
24. As a reader opening the item with no `?muc=` (or an unknown one), I want to land on the first Entry of the Book, Phần thứ nhất Essay 1, so that the book reads from its beginning.
25. As a reader, I want "previous" and "next" buttons at the end of each Entry, so that I can read straight through without returning to the contents panel.
26. As a reader, I want previous/next to follow book order across Section and Part boundaries (the last Phần thứ nhất Essay leads to the Phần thứ hai Part Introduction, and so on), so that the whole Book reads continuously.
27. As a reader on the first or last Entry, I want the missing direction hidden or disabled, so that I don't hit a dead link.
28. As a reader, I want switching Entries not to reload the page or jump the scroll unexpectedly, so that reading feels smooth.
29. As a reader, I want Footnote markers in Essays and Part Introductions to open the same citation popover as in Stories, so that scholarly notes work everywhere.
30. As a reader, I want Footnotes matched correctly even though the source restarts numbering on every printed page, so that each marker shows its own note.
31. As a reader, I want a Story's Khảo dị section rendered as it is today, so that variant versions stay readable.
32. As an English-locale visitor, I want the English Strapi title and abstract plus an English interface (contents title, search, tabs, introduction label, empty state, previous/next, footnote labels), so that I can navigate the Vietnamese text.
33. As a Vietnamese-locale visitor, I want the same interface in Vietnamese, so that the page is consistent with the rest of the site.
34. As a reader on a phone, I want the contents panel stacked above the text, as the reader does today, so that the page works on small screens.
35. As a keyboard or screen-reader user, I want Part tabs, list items, footnote markers and previous/next to be focusable and labelled, so that the reader is accessible.
36. As a search engine or link-preview service, I want the page's metadata title to reflect the open Entry, so that shared links describe what they point to.
37. As a maintainer, I want the reader to read the Book's structure only from the extraction's root table of contents, so that re-running the extraction updates the site with no hand-kept list.
38. As a maintainer, I want a server log warning listing Entries whose Footnote marker and definition counts disagree, so that extraction defects get noticed and fixed upstream.

## Implementation Decisions

- **Remove the stand-alone collection completely.** The stand-in route folder (its `[itemid]` reader route, data, components and the Strapi stand-in module), the placeholder card injection on the `/our-collections` listing, and the slug redirect on the collection page all go. No redirect is added, so the old URL 404s.
- **Relocate the reader beside the other custom Item Viewers.** It moves into the Collection Item page's `searchable-text` area, next to Truyện Kiều and Lục Vân Tiên. It is wired as one more branch of the item page's `collectionId && documentId` chain, matching `vietnamese-folk-literature` + `truyen-co-tich-viet-nam`, and replacing the Mirador fallback for that item only. The item page keeps its Strapi-driven header, breadcrumb, permalink and metadata block. The reader's own header and placeholder copy go away.
- **Book data module (server-only)** replaces the old section-folder aggregator. It reads the root `table_of_contents.json` under the `extracted_stories` folder of the Book's public data, and the per-Entry markdown at `<folder>/<markdown_file>`, or a Part's `introduction` path. Its interface:
  - the ordered list of Parts, each carrying its number, full title, optional Part Introduction Entry, and Sections (id, title, Entries);
  - the flat list of Entries in book order: per Part, its Part Introduction (if any), then its Sections in TOC order, then Entries by printed number;
  - lookup of an Entry by `muc` slug, returning the Entry, its previous/next neighbours (or none), and its parsed body + Footnotes;
  - the default Entry, which is the first in book order.
- **Entry shape:** kind (`story` / `essay` / `part-introduction`), `muc` slug, Part number, Section id and title (none for a Part Introduction), printed number (none for a Part Introduction), title, Khảo dị flag (Stories only), Footnote count.
- **`muc` slug scheme**, derived from the TOC and never hand-maintained:
  - Story: `truyen-<story_number>`. Story numbers are unique across the Book.
  - Essay: `phan-<part_number>-muc-<section_id lowercased>-bai-<essay_number>`, e.g. `phan-1-muc-ii-bai-3`.
  - Part Introduction: `phan-<part_number>-loi-dan`.
  - The module asserts slug uniqueness when it builds the index and fails loudly on a collision.
- **Part Introduction title:** the TOC has no title for introductions, so the list shows the localised "Lời dẫn" / "Introduction" label. The heading inside the markdown (the Part's title) renders as the body's heading.
- **Markdown parsing is unchanged.** The existing positional Footnote parser (k-th marker pairs with the k-th definition under the `--- / ### Chú thích` delimiter) already handles Essays and Part Introductions, which use the same format. The Footnote-mismatch warning is kept and runs over every Entry.
- **URL contract:** the selected Entry lives in the `?muc=` search param on the Collection Item URL. A missing or unknown value renders the default Entry, with no redirect. Page metadata uses the Entry's title when `?muc=` resolves, otherwise Strapi's item title.
- **Contents panel (client):** a title bar, a search input, Part tabs (short label, full title as tooltip and as a line under the tabs), and a scroll list grouped by Section with the Part Introduction first. The active tab defaults to the open Entry's Part. While the search query is non-empty, the list shows matches from all Parts, grouped by Part then Section, and the tabs don't filter. Search is title-only with the site's existing diacritic-insensitive normaliser. Selecting an Entry uses `router.replace` with `scroll: false` inside a transition, as today.
- **Previous/next:** rendered below the Entry body, as links to the neighbours' `?muc=` URLs computed on the server. A direction with no neighbour isn't rendered.
- **Localisation:** a new `KhoTangTruyen` block in both locale message files, holding the contents title, search placeholder and label, Part tab label (`{n}`), Part Introduction label, no-results text, previous and next, and the Footnote aria label (`{n}`). Book text, TOC titles and in-markdown headings ("Chú thích", "KHẢO DỊ") are source content and aren't translated.

## Testing Decisions

- **No automated tests.** The website repo has no test runner, and adding one is out of scope. All verification is a manual browser check against `next dev`. Good checks exercise externally visible behaviour (URLs, rendered text, navigation), not internal structure.
- **Static checks:** the project's type-check and lint pass for the touched files.
- **Manual acceptance checklist:**
  - `/vi/our-collections/vietnamese-folk-literature/truyen-co-tich-viet-nam` shows the Strapi title and abstract, a breadcrumb to "Văn học Dân gian Việt Nam", the reader opened on Phần thứ nhất Essay 1, and the metadata block. No Mirador.
  - `/en/...` with the same path shows "Treasury of Vietnamese Folktales" and an English interface, with Vietnamese body text.
  - `/vi/our-collections/kho-tang-truyen-co-tich-viet-nam/doc-truyen` and `/vi/our-collections/kho-tang-truyen-co-tich-viet-nam` both return 404. `/vi/our-collections` has no placeholder Kho Tàng card.
  - Each Part tab lists the right Sections and counts: Phần 1 has I–III with 6/5/4 Essays, Phần 2 has Lời dẫn and I–X with 201 Stories, Phần 3 has Lời dẫn and IV–V with 4/4 Essays.
  - `?muc=truyen-2` renders "Sự tích trầu, cau và vôi", its Khảo dị, and working Footnote popovers. `?muc=phan-1-muc-i-bai-1` renders with its Footnotes. `?muc=phan-3-loi-dan` renders. `?muc=bogus` falls back to Phần 1 Essay 1.
  - Previous/next crosses boundaries correctly: the last Phần 1 Essay → `phan-2-loi-dan` → `truyen-1`, the last Story → `phan-3-loi-dan`. The first Entry has no "previous" and the last has no "next".
  - Searching "su tich" with the Phần 1 tab active still lists Phần 2 Stories. A nonsense query shows the empty-state text.
  - Narrow viewport: the panel stacks above the text with no horizontal scroll.
  - The server log shows the Footnote-mismatch warning, if any, once per process.
- **Prior art:** the existing reader was verified the same way. Other custom Item Viewers (Truyện Kiều, Tinh hoa mùa xuân) also have no automated tests.

## Out of Scope

- Full-text search over Entry bodies.
- Translating the Book's text or TOC titles.
- Fixing extraction defects such as Footnote count mismatches or merged Footnotes. Those belong to the extraction pipeline's own tickets (`.scratch/book-parts-extraction/issues/`).
- Adding a test runner to the website repo.
- Changing the Strapi records (title, abstract, metadata, `item_url`) or the `vietnamese-folk-literature` Collection page.
- Linking Entries to page images or a Mirador view of the printed book.
- A redirect from the old stand-alone URL.

## Further Notes

- Strapi facts verified on 2026-10-01: the item slug is `truyen-co-tich-viet-nam` in both `vi` and `en`, it belongs only to `vietnamese-folk-literature`, and `item_url` is empty. The item page's generic `documentType` logic is therefore `document`, which is what triggers Mirador. The new branch must sit ahead of that fallback.
- Data facts: the root TOC lists 3 Parts. Phần thứ nhất has `introduction: null`. Phần thứ hai and Phần thứ ba each have an `introduction.md`. Section folders are given by each Section's `folder` field, and Essay filenames (`essay_NN.md`) repeat across folders, so Entries must never be keyed by filename.
- Per the global rule, nothing gets committed. The developer reviews and commits.
