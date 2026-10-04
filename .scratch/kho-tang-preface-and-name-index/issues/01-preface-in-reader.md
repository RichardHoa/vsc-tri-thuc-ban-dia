# 01: Preface (Lời nói đầu) in the reader

**What to build:** A reader can read the author's Lời nói đầu (PDF pages 21–22) as the Book's Preface. It is the first Entry under the Phần thứ nhất tab and the first in book order, and the Book opens on it. See `../spec.md` (Preface sections). Repo: `digitizing-vietnam-website`. Glossary: that repo's `CONTEXT.md`.

**Blocked by:** None (can start immediately)

**Status:** done (uncommitted, awaiting review)

- [x] The Preface markdown is written by hand from PDF pages 21–22 (in `vsc-tri-thuc-ban-dia/data.pdf`): `ñ` → `đ`, line breaks rejoined into paragraphs, 1957 spelling kept. Placed in the published Kho Tàng data and referenced from a top-level `preface` field in `table_of_contents.json`.
- [x] `?muc=loi-noi-dau` renders the Preface, with "Hà-nội, tháng VI năm 1957" and "NGUYỄN ĐỔNG CHI" right-aligned.
- [x] It is listed first under the Phần 1 tab, labelled "Lời nói đầu" (not the "Lời dẫn" introduction label). Phần 1 still has no Part Introduction.
- [x] The default reader URL and an unknown `?muc=` open the Preface.
- [x] The Preface has no "previous". Its "next" is Phần 1 Essay 1, whose "previous" is the Preface.
- [x] Entry-title search for "loi noi dau" finds it.
- [x] Type-check and lint pass for the touched files.
