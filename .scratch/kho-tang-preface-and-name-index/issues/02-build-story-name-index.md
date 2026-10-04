# 02: Build the Story Name Index JSON

**What to build:** A one-off builder in `vsc-tri-thuc-ban-dia` turns the printed Story Name Index (PDF pages 1518–1551) into the editable Index Name JSON in the website's published Kho Tàng data. Each name is resolved against the published Story text, so the in-text spelling is recorded (*A-đao dũng cảm* → *A-dao dũng cảm*). It also produces a report of names it could not resolve, for the maintainer to fix by hand. See `../spec.md` (Story Name Index builder; the record shape is there). Do NOT recreate the deleted extracted folder: read Story text only from the website's published copy.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Parses every index record: wrapped names, `, <qualifier>` suffixes, `Xem X` aliases, nameless continuation records (extra target for the previous name), and the three locations (Story / Khảo dị / Chú thích). `ñ` → `đ`. Page heading, intro paragraph and page numbers are skipped.
- [x] Resolves each target against that Story's markdown: exact match (case-insensitive, whitespace/hyphens loosened), then ignoring diacritics with đ/d treated alike, then a conservative fuzzy match. Stores `textName` when found. For Chú thích targets, also records which Footnote holds the name.
- [x] Writes the JSON into the website's Kho Tàng public data, and prints and saves the unresolved report with counts.
- [x] Minimal pytest file (about six cases, through the builder's single entry point, using fixture index text and a tiny fixture Story folder): A-đao → A-dao, qualifier, Xem alias, two-target continuation, wrapped name, one unresolvable name.
- [x] Builder run once on the real data. The unresolved report is handed to the maintainer for manual fixes.

## Comments

- Built by `build_name_index.py` (`extractor/name_index.py`, tests in `tests/test_name_index.py`); output `story_name_index.json` (a plain JSON array of IndexName records) in the website's Kho Tàng data folder. Run: `python3 build_name_index.py --data-dir <website>/public/data/kho-tang-truyen-co-tich-viet-nam`.
- Unresolved report: `../unresolved-index-names.md` (kept out of the public folder deliberately). It also lists targets resolved only by fuzzy match, for review.
- Printed-index quirks handled: "Chú thích" glued to or after a name (overrides the Khảo dị column → `chu-thich`; 19 such targets, not ~9), name lines spilling onto the next page, `[50]`, stray `tạp`, comma-less qualifiers on their own line, Xem targets that name only the first half of an "X hay là Y" name.
