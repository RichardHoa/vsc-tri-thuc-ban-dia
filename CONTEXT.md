# Kho Tàng Truyện Cổ Tích Việt-Nam extraction

Turns the printed anthology *Kho Tàng Truyện Cổ Tích Việt-Nam* (Nguyễn Đổng Chi) into structured text that mirrors the book's own MỤC LỤC.

## Language

### Book structure

**Part**:
One of the book's three top-level divisions (*Phần thứ nhất*, *Phần thứ hai*, *Phần thứ ba*). Part 1 and Part 3 are scholarly prose; Part 2 is the anthology of tales.
_Avoid_: section, phần (in code/docs)

**Section**:
A Roman-numeral group inside a **Part** (e.g. *I. NGUỒN GỐC SỰ VẬT*, *IV. ĐẶC ĐIỂM CỦA TRUYỆN CỔ TÍCH VIỆT-NAM*). Roman numerals are not unique across the book: Part 3 continues Part 1's numbering (IV, V), which collides with Part 2's IV and V.
_Avoid_: chapter, category

**Story**:
A numbered tale in Part 2 (*1. SỰ TÍCH DƯA HẤU* … *201. HAI BẢY MƯỜI BA*). Numbering runs continuously across the whole Part, and may carry a **Khảo dị**.
_Avoid_: tale, truyện (in code/docs)

**Essay**:
A numbered scholarly subsection inside a **Section** of Part 1 or Part 3 (e.g. *1. PHÂN LOẠI TRUYỆN CỔ, MỘT VẤN ĐỀ ĐẶT RA TỪ LÂU…*). Numbering restarts in every Section.
_Avoid_: article, subsection, chapter

**Introduction**:
Unnumbered prose that opens a **Part** before its first **Section** (Part 2's editorial preface; Part 3's opening remarks). Part 1 has none.
_Avoid_: preface, lời dẫn (that is the book's own front matter, outside every Part)

**Khảo dị**:
The comparative-variants note printed after some **Stories**, listing related versions from other regions or peoples.

**MỤC LỤC**:
The book's printed table of contents (PDF pages 4–19), the reference for the Part → Section → Story/Essay hierarchy.
_Avoid_: TOC (except for the generated `table_of_contents.json`)

**Bibliography** (*Thư mục tham khảo*):
The book's reference list (pages 1435–1466), the one piece of back matter that is extracted. It opens with prose and an abbreviation key, then three **Sections** (*I. SÁCH VÀ BÀI*, *II. BÁO VÀ TẠP CHÍ*, *III- TÀI LIỆU CHÉP TAY*) of **Bibliography entries**. It sits after Part 3 like a fourth sibling but is not a **Part**.
_Avoid_: Part 4, phần thứ tư

**Bibliography entry**:
One cited work in a Bibliography **Section** (a book, article, periodical or manuscript).
_Avoid_: reference, citation

**Volume** (*tập*):
A print-binding division (Tập I–V). Part 2 is split across all five; a Volume boundary is not a structural level.

## Relationships

- A **Part** contains zero or one **Introduction**, then one or more **Sections**
- Front matter (pages 20–41) and back matter (from LỜI SAU SÁCH, page 1434) belong to no **Part**; of the back matter only the **Bibliography** is extracted
- **MỤC LỤC** is the guide, the printed text is the authority: Part 3 Section V's Essay 1 is printed but missing from MỤC LỤC, and is still an **Essay**
- A heading (of a **Part**, **Section**, **Story** or **Essay**) can carry a footnote of its own
- A **Section** in Part 2 contains **Stories**; a **Section** in Part 1 or Part 3 contains **Essays**; a **Section** of the **Bibliography** contains **Bibliography entries**
- The **Bibliography**'s Section III is printed but missing from **MỤC LỤC**, and is still a **Section**
- A **Story** has zero or one **Khảo dị**
- A **Section** can span a **Volume** boundary (Section III of Part 2 starts in Tập I and continues in Tập II)

## Example dialogue

> **Dev:** "Extract Section IV."
> **Domain expert:** "Which Part? Part 2's IV is *Thông minh, tài trí và sức khỏe*, which is Stories. Part 3's IV is *Đặc điểm của truyện cổ tích Việt-Nam*, which is Essays."

## Flagged ambiguities

- "section" was used for a **Part** ("the first section, from page 42"). Resolved: a Part is *Phần*, a Section is a Roman-numeral group inside it.
