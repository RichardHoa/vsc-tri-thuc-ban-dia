# 03: Search and highlight Index Names in the reader

**What to build:** In the Kho Tàng reader, the existing search box also finds Index Names. Clicking one opens its Story, highlights every occurrence of the name in yellow (using the Story text's spelling), and scrolls to the right place. See `../spec.md` (Reader: search / highlight, and the manual checklist). Repo: `digitizing-vietnam-website`.

**Blocked by:** 02 (Build the Story Name Index JSON)

**Status:** done (uncommitted, awaiting review)

- [x] Search shows a second result group of Index Names (one row per name × target) under the Entry-title groups. It matches both the printed and the in-text spelling, ignoring case and diacritics. Rows show the name, a grey qualifier, the target Story, and a location label. Strings are localised in vi/en.
- [x] Clicking a row opens `?muc=truyen-N&ten=<textName>` (plus the Footnote param for Chú thích). Reloading keeps the highlight. Opening another Entry clears it.
- [x] One pure matcher (case-insensitive, diacritics exact, whitespace/hyphens loosened, whole name only) drives yellow `<mark>`s across the Story body, headings, Khảo dị and Footnote bodies.
- [x] Scrolls to the first match. For Chú thích, scrolls to the target Footnote marker, opens its popover and highlights the name inside.
- [x] Footnote markers whose body contains a match are styled yellow. Other popovers are not auto-opened.
- [x] An unresolved target opens the Story at the top with no highlight.
- [x] The spec's manual checklist passes. Type-check and lint pass.

## Comments

- From ticket 02: a target's `footnote` is the **1-based** ordinal string of the Footnote definition under "Chú thích" — the reader's `#fn-i` index is `Number(footnote) - 1`.
- A record can have `targets: []` (e.g. *Thử thần và miêu thần*, which has no Story number in the print). Show no rows for it.
- `textName` can contain a comma the printed name lacks (e.g. *Hồn Trương Ba, da hàng thịt*); highlight with `textName`, not `printed`.
- Implemented (website, uncommitted): `findNameMatches.ts` is the pure matcher. `data.ts` `getIndexNameRows()` flattens the JSON into one row per (name, target). The reader adds a search group plus `?ten=` / `?chu-thich=` (1-based); `renderStoryBlocks` takes a `highlight` option; `FootnotePopover` gets `highlighted` / `autoOpen`.
- Search loosens whitespace and hyphens (and Entry-title search now does the same), so "a dao" finds *A-dao*.
- Checked in headless Chrome against `next dev`: A-dao, Ba anh em qualifiers, Cao phi viễn tẩu alias, Chú thích (92, fn 6) popover open with the name highlighted, Entry click clears `ten`, no overflow at 375px. All resolved targets highlight in real text. A name with a footnote marker inside (Story titles 25 and 47, `hoa lài[^1] cắm`) matches with the marker read as one space, and its `<mark>` is split around the Footnote button.
- Known limitations:
  - An unresolved target keeps the current scroll position, like any Entry click. No target is currently unresolved.
- Data, not code: *Xử phiến đá* has only target 110, so the checklist's "two rows (110, 120)" needs the 120 target added to the JSON. *Khiên Ngưu Chức Nữ* (truyện khác → 182) appears twice.
- Changed on the maintainer's request:
  - Search now lists only Index Names. Entry-title matching is removed, which replaces the spec's "two groups, Entry titles first" and ticket 01's "Entry-title search for 'loi noi dau'".
  - While the box has a query, the results replace the tab's contents.
  - Scrolling to the highlight or the target Footnote is smooth.
