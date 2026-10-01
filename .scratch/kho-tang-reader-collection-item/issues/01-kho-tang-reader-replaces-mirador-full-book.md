# 01: Kho Tàng reader replaces Mirador on `truyen-co-tich-viet-nam`, covering the full Book

**What to build:** A reader opening the Collection Item `truyen-co-tich-viet-nam` in the `vietnamese-folk-literature` Collection reads the whole Book instead of an empty Mirador viewer. The Strapi title, abstract, breadcrumb and metadata block stay as they are. Between them sits the Kho Tàng reader, which now holds:
- a contents panel with one tab per Part, each listing its Part Introduction ("Lời dẫn") and then its Sections' Stories or Essays;
- title search across the whole Book;
- previous/next navigation in book order across Section and Part boundaries;
- a readable `?muc=` link for every Entry (`truyen-62`, `phan-1-muc-ii-bai-3`, `phan-3-loi-dan`), opening at Phần thứ nhất Essay 1 when the link is missing or unknown.

The Book's structure comes only from the extraction's root table of contents. The reader's interface text is localised (vi/en), and the Book's text stays Vietnamese. The old stand-alone collection is removed entirely, and its URLs return 404.

Full detail: `../spec.md`. Glossary: `CONTEXT.md` in the website repo.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] **Old collection removed:**
  - [ ] The stand-alone Kho Tàng collection's route, data, components and Strapi stand-in are deleted.
  - [ ] The placeholder card no longer appears on `/our-collections`.
  - [ ] The slug redirect on the collection page is removed.
  - [ ] `/vi/our-collections/kho-tang-truyen-co-tich-viet-nam` and `.../doc-truyen` return 404.
- [ ] **Item page wiring:**
  - [ ] The reader lives beside the other custom Item Viewers.
  - [ ] It renders for `vietnamese-folk-literature` + `truyen-co-tich-viet-nam` ahead of the Mirador fallback.
  - [ ] Other items' viewers are unchanged.
- [ ] **Item page in each locale:**
  - [ ] `/vi/.../vietnamese-folk-literature/truyen-co-tich-viet-nam` shows the Strapi title and abstract, a breadcrumb to "Văn học Dân gian Việt Nam", the reader, and the metadata block. No Mirador.
  - [ ] `/en/...` shows "Treasury of Vietnamese Folktales" with an English interface and Vietnamese body text.
- [ ] **Book data:**
  - [ ] The Book is built from the root TOC.
  - [ ] Entries follow book order: per Part, the Part Introduction first, then Sections in TOC order, then printed number.
  - [ ] `muc` slugs are derived from the TOC, and a slug collision fails loudly.
  - [ ] Entries are never keyed by filename.
- [ ] **Part tabs:**
  - [ ] Labelled "Phần 1/2/3" (vi) or "Part 1/2/3" (en), with the full Part title as a tooltip and as a line under the tabs.
  - [ ] The active tab follows the open Entry's Part.
  - [ ] Phần 1 lists I–III with 6/5/4 Essays.
  - [ ] Phần 2 lists Lời dẫn and I–X with 201 Stories.
  - [ ] Phần 3 lists Lời dẫn and IV–V with 4/4 Essays.
- [ ] **Search:**
  - [ ] It matches titles across all Parts while a query is typed, ignoring diacritics and case. "su tich" finds Phần 2 Stories while the Phần 1 tab is active.
  - [ ] Results are grouped by Part and Section.
  - [ ] A query with no match shows the localised empty-state text.
- [ ] **`?muc=` links:**
  - [ ] `truyen-2` renders "Sự tích trầu, cau và vôi" with its Khảo dị and working Footnote popovers.
  - [ ] `phan-1-muc-i-bai-1` renders with its Footnotes.
  - [ ] `phan-3-loi-dan` renders.
  - [ ] `bogus` and a missing param both render Phần 1 Essay 1.
  - [ ] The page metadata title shows the open Entry's title.
- [ ] **Previous/next:**
  - [ ] Links sit below each Entry and follow book order: the last Phần 1 Essay leads to `phan-2-loi-dan`, which leads to `truyen-1`, and the last Story leads to `phan-3-loi-dan`.
  - [ ] There is no "previous" on the first Entry and no "next" on the last.
  - [ ] Switching Entries doesn't reload the page or jump the scroll.
- [ ] **Localisation:** the interface text (contents title, search placeholder and label, Part tab label, Part Introduction label, no-results, previous/next, Footnote aria label) comes from a new `KhoTangTruyen` block in both locale message files. Nothing user-facing stays hard-coded in Vietnamese.
- [ ] **Footnote check:** the Footnote-mismatch server warning covers every Entry and logs once per process.
- [ ] **Narrow viewport:** the contents panel stacks above the text with no horizontal scroll.
- [ ] **Static checks:** type-check and lint pass for the touched files.
- [ ] **Hand-off:** nothing is committed, so the developer can review and commit.
